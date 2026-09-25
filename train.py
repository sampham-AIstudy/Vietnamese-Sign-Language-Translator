"""
Training Script for Vietnamese Sign Language Recognition (VSLR) Baseline Model
Usage:
  python train.py --config configs/experiments/baseline_bigru.yaml
  python train.py --config configs/experiments/baseline_bigru.yaml --smoke-test
"""

import os
import sys
import yaml
import argparse
import torch

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.models.baseline_bigru import BaselineBiGRU
from src.models.stgcn_model import STGCNModel
from src.models.transformer_model import TransformerModel
from src.data.vsl_dataset import get_vsl_dataloaders
from src.training.trainer import VSLTrainer


def parse_args():
    parser = argparse.ArgumentParser(description="Train VSLR Baseline Model")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/experiments/baseline_bigru.yaml",
        help="Path to YAML experiment configuration file",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Override total epochs from config",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override batch size from config",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=None,
        help="Override learning rate from config",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run 2 epochs smoke test to verify pipeline, loss change, and checkpointing",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Limit number of batches per epoch (useful for smoke tests)",
    )
    return parser.parse_args()


def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    args = parse_args()
    config = load_config(args.config)

    # CLI overrides
    epochs = args.epochs or config["training"]["epochs"]
    batch_size = args.batch_size or config["training"]["batch_size"]
    lr = args.lr or config["training"]["lr"]
    max_batches = args.max_batches

    if args.smoke_test:
        epochs = 2
        if max_batches is None:
            max_batches = 2
        print(f"=== RUNNING IN SMOKE TEST MODE ({epochs} EPOCHS, {max_batches} BATCHES/EPOCH) ===")

    print(f"Loading experiment configuration: {args.config}")
    print(f"Experiment: {config.get('experiment_name', 'Unnamed')}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Compute Device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    # 1. Initialize DataLoaders
    data_cfg = config["data"]
    print(f"\nInitializing DataLoaders for Tier: {data_cfg['tier']} (Batch size={batch_size})...")
    train_loader, val_loader, test_loader, label_map = get_vsl_dataloaders(
        tier=data_cfg["tier"],
        batch_size=batch_size,
        num_workers=config["training"].get("num_workers", 0),
        keypoints_dir=data_cfg.get("keypoints_dir", "data/extracted_keypoints"),
        target_len=data_cfg.get("sequence_length", 60),
    )
    print(f"Classes in dataset: {len(label_map)}")
    num_classes = len(label_map)

    # 2. Build Model
    model_cfg = config["model"]
    print(f"\nBuilding Model: {model_cfg['name']}...")
    if model_cfg["name"] == "TransformerModel":
        model = TransformerModel(
            num_joints=model_cfg.get("num_joints", 67),
            coord_dim=model_cfg.get("coord_dim", 3),
            d_model=model_cfg.get("d_model", 128),
            nhead=model_cfg.get("nhead", 4),
            dim_feedforward=model_cfg.get("dim_feedforward", 256),
            num_layers=model_cfg.get("num_layers", 2),
            num_classes=num_classes,
            dropout=model_cfg.get("dropout", 0.1),
            pos_encoding=model_cfg.get("pos_encoding", "sinusoidal"),
            pooling_type=model_cfg.get("pooling_type", "attention"),
            norm_first=model_cfg.get("norm_first", True),
        )
    elif model_cfg["name"] == "STGCNModel":
        model = STGCNModel(
            num_joints=model_cfg.get("num_joints", 67),
            in_channels=model_cfg.get("in_channels", 3),
            num_classes=num_classes,
            graph_strategy=model_cfg.get("graph_strategy", "spatial"),
            channel_dims=model_cfg.get("channel_dims", [64, 64, 128]),
            dropout=model_cfg.get("dropout", 0.25),
            temporal_kernel_size=model_cfg.get("temporal_kernel_size", 9),
        )
    else:
        model = BaselineBiGRU(
            num_joints=model_cfg.get("num_joints", 67),
            coord_dim=model_cfg.get("coord_dim", 3),
            hidden_dim=model_cfg.get("hidden_dim", 128),
            num_layers=model_cfg.get("num_layers", 2),
            num_classes=num_classes,
            dropout=model_cfg.get("dropout", 0.3),
            bidirectional=model_cfg.get("bidirectional", True),
            pooling_type=model_cfg.get("pooling_type", "attention"),
        )

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total Trainable Parameters: {total_params:,}")

    # 3. Setup Trainer
    train_cfg = config["training"]
    out_cfg = config["output"]

    trainer = VSLTrainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        lr=lr,
        weight_decay=train_cfg.get("weight_decay", 1e-4),
        patience=train_cfg.get("patience", 10),
        checkpoint_path=out_cfg.get("checkpoint_file", "checkpoints/baseline_bigru.pt"),
        history_path=out_cfg.get("history_file", "experiments/baseline/history.json"),
        device=device,
        use_amp=train_cfg.get("use_amp", True),
        max_grad_norm=train_cfg.get("max_grad_norm", 1.0),
        max_batches=max_batches,
    )

    # 4. Train
    print(f"\nStarting training loop for {epochs} epoch(s)...")
    summary = trainer.fit(epochs=epochs, verbose=True)

    # 5. Smoke Test Verification
    if args.smoke_test:
        print("\n[SMOKE TEST VERIFICATION]")
        assert os.path.exists(summary["checkpoint_path"]), "Checkpoint was not saved!"
        assert os.path.exists(summary["history_path"]), "History JSON was not saved!"
        
        # Test loading checkpoint
        ckpt = torch.load(summary["checkpoint_path"], map_location=device, weights_only=False)
        assert "model_state_dict" in ckpt, "Invalid checkpoint format!"
        model.load_state_dict(ckpt["model_state_dict"])
        print(f"Checkpoint successfully reloaded. Best Val Top-1: {ckpt['val_top1']}%.")
        print(">>> SMOKE TEST PASSED SUCCESSFULLY! <<<")

    return summary


if __name__ == "__main__":
    main()
