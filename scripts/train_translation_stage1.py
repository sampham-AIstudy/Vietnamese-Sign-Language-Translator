"""
Stage 1: Auxiliary Syntax Reordering Pretraining on Cleaned 10K Parallel Text
Model: VietAI/vit5-base
Data: data/external/parallel_text/vie_vsl_10k_cleaned.jsonl (7,140 pairs)
Output: checkpoints/vit5_stage1/best_model
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

from src.translation.dataset import Clean10kDataset, get_seq2seq_collate_fn


def train_stage1(
    model_name: str = "VietAI/vit5-base",
    batch_size: int = 8,
    grad_accum_steps: int = 2,
    epochs: int = 3,
    lr: float = 5e-5,
    seed: int = 42,
    checkpoint_dir: str = "checkpoints/vit5_stage1",
    reports_dir: str = "reports",
):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[STAGE 1] Training on device: {device}")
    if device.type == "cuda":
        print(f"[STAGE 1] GPU: {torch.cuda.get_device_name(0)}")

    ckpt_path = project_root / checkpoint_dir
    best_model_path = ckpt_path / "best_model"
    best_model_path.mkdir(parents=True, exist_ok=True)
    rep_path = project_root / reports_dir
    rep_path.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(device)

    # Prepare Datasets & Loaders
    collate_fn = get_seq2seq_collate_fn(tokenizer, max_source_length=128, max_target_length=128)

    train_dataset = Clean10kDataset(split="train", val_ratio=0.1, seed=seed)
    val_dataset = Clean10kDataset(split="val", val_ratio=0.1, seed=seed)

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

    print(f"[STAGE 1] Dataset loaded: Train={len(train_dataset)} pairs, Val={len(val_dataset)} pairs")
    print(f"[STAGE 1] Effective batch size: {batch_size * grad_accum_steps}, Steps per epoch: {len(train_loader) // grad_accum_steps}")

    # Optimizer & Scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    total_training_steps = (len(train_loader) // grad_accum_steps) * epochs
    warmup_steps = int(0.1 * total_training_steps)
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_training_steps
    )
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

    best_val_loss = float("inf")
    history = []
    start_total_time = time.time()

    for epoch in range(1, epochs + 1):
        epoch_start = time.time()
        model.train()
        train_loss = 0.0
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )
                loss = outputs.loss / grad_accum_steps

            scaler.scale(loss).backward()
            train_loss += loss.item() * grad_accum_steps

            if (step + 1) % grad_accum_steps == 0 or (step + 1) == len(train_loader):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
                scheduler.step()

            if (step + 1) % 200 == 0:
                print(f"  [Epoch {epoch}/{epochs}] Step {step+1}/{len(train_loader)} | Batch Loss: {loss.item()*grad_accum_steps:.4f} | LR: {scheduler.get_last_lr()[0]:.2e}")

        avg_train_loss = train_loss / len(train_loader)

        # Validation phase
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

        print(f"\n>>> [Epoch {epoch}/{epochs} Complete] Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} | Time: {epoch_time:.1f}s")

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
            print(f"  --> Saved new best Stage 1 checkpoint to: {best_model_path} (Val Loss: {best_val_loss:.4f})")
            model.save_pretrained(best_model_path)
            tokenizer.save_pretrained(best_model_path)

    total_time = time.time() - start_total_time
    summary = {
        "model_name": model_name,
        "dataset": "vie_vsl_10k_cleaned.jsonl",
        "train_samples": len(train_dataset),
        "val_samples": len(val_dataset),
        "total_epochs": epochs,
        "best_val_loss": round(best_val_loss, 4),
        "total_training_time_sec": round(total_time, 2),
        "history": history,
    }

    hist_file = rep_path / "vit5_stage1_history.json"
    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n[STAGE 1 COMPLETE] Best Val Loss: {best_val_loss:.4f} in {total_time:.1f}s")
    print(f"[STAGE 1] Saved history log to: {hist_file}")
    return best_model_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=5e-5)
    args = parser.parse_args()

    train_stage1(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
    )
