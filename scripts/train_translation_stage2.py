"""
Stage 2: Primary Domain Fine-Tuning on VSL-GH Canonical Sentences
Base Model: checkpoints/vit5_stage1/best_model (Pretrained ViT5)
Data: data/external/vsl_gh/dataset_canonical.json
Split:
  - Train: SENT001..SENT240 (240 sentences)
  - Val:   SENT241..SENT270 (30 sentences)
  - Test:  SENT271..SENT300 (30 sentences held out)
Output: checkpoints/vit5_stage2/best_model
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    get_cosine_schedule_with_warmup,
)

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.translation.dataset import VSLGHTextDataset, get_seq2seq_collate_fn


def train_stage2(
    pretrained_stage1_path: str = "checkpoints/vit5_stage1/best_model",
    batch_size: int = 8,
    epochs: int = 15,
    lr: float = 2.5e-5,
    patience: int = 5,
    seed: int = 42,
    checkpoint_dir: str = "checkpoints/vit5_stage2",
    reports_dir: str = "reports",
):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[STAGE 2] Fine-tuning on device: {device}")
    if device.type == "cuda":
        print(f"[STAGE 2] GPU: {torch.cuda.get_device_name(0)}")

    ckpt_path = project_root / checkpoint_dir
    best_model_path = ckpt_path / "best_model"
    best_model_path.mkdir(parents=True, exist_ok=True)
    rep_path = project_root / reports_dir
    rep_path.mkdir(parents=True, exist_ok=True)

    stage1_full_path = project_root / pretrained_stage1_path
    if not stage1_full_path.exists():
        print(f"[WARN] Stage 1 checkpoint not found at {stage1_full_path}, falling back to raw 'VietAI/vit5-base'")
        model_source = "VietAI/vit5-base"
    else:
        print(f"[STAGE 2] Loading Stage 1 pretrained checkpoint from: {stage1_full_path}")
        model_source = str(stage1_full_path)

    tokenizer = AutoTokenizer.from_pretrained(model_source)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_source).to(device)

    # Datasets
    collate_fn = get_seq2seq_collate_fn(tokenizer, max_source_length=128, max_target_length=128)
    train_dataset = VSLGHTextDataset(split="train")
    val_dataset = VSLGHTextDataset(split="val")

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=0,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=0,
    )

    print(f"[STAGE 2] VSL-GH Datasets: Train={len(train_dataset)} sentences, Val={len(val_dataset)} sentences")

    # Optimizer with conservative learning rate to prevent overfitting on 240 samples
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    warmup_steps = int(0.1 * total_steps)
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

    best_val_loss = float("inf")
    patience_counter = 0
    best_epoch = 0
    history = []
    start_total_time = time.time()

    for epoch in range(1, epochs + 1):
        epoch_start = time.time()
        model.train()
        train_loss = 0.0

        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            optimizer.zero_grad()
            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )
                loss = outputs.loss

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

            train_loss += loss.item()

        avg_train_loss = train_loss / len(train_loader)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)

                with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                    outputs = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels,
                    )
                val_loss += outputs.loss.item()

        avg_val_loss = val_loss / len(val_loader)
        epoch_time = time.time() - epoch_start

        print(f"[Stage 2 | Epoch {epoch:02d}/{epochs:02d}] Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} | LR: {scheduler.get_last_lr()[0]:.2e} ({epoch_time:.1f}s)")

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 4),
            "val_loss": round(avg_val_loss, 4),
            "lr": float(scheduler.get_last_lr()[0]),
            "epoch_time_sec": round(epoch_time, 2),
        }
        history.append(epoch_record)

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_epoch = epoch
            patience_counter = 0
            print(f"  --> Saved new best Stage 2 model: {best_model_path} (Val Loss: {best_val_loss:.4f})")
            model.save_pretrained(best_model_path)
            tokenizer.save_pretrained(best_model_path)
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"\n[EARLY STOPPING] Validation loss did not improve for {patience} epochs. Halting.")
                break

    total_time = time.time() - start_total_time
    summary = {
        "base_model": model_source,
        "train_samples": len(train_dataset),
        "val_samples": len(val_dataset),
        "best_epoch": best_epoch,
        "best_val_loss": round(best_val_loss, 4),
        "total_training_time_sec": round(total_time, 2),
        "history": history,
    }

    hist_file = rep_path / "vit5_stage2_history.json"
    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n[STAGE 2 COMPLETE] Best Epoch: {best_epoch} with Val Loss: {best_val_loss:.4f} in {total_time:.1f}s")
    print(f"[STAGE 2] Saved log to: {hist_file}")
    return best_model_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage1-path", type=str, default="checkpoints/vit5_stage1/best_model")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=2.5e-5)
    parser.add_argument("--patience", type=int, default=5)
    args = parser.parse_args()

    train_stage2(
        pretrained_stage1_path=args.stage1_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
    )
