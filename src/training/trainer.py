"""
Production-Ready PyTorch Trainer for VSLR Models
Features:
- Mixed Precision (torch.amp) for RTX 3050 (4GB)
- Masked Input Handling (sequences, joint_masks, temporal_masks)
- ReduceLROnPlateau Scheduler
- Early Stopping on Validation Loss
- Best Checkpoint Retention
- JSON History Logging
"""

import os
import time
import json
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau
from typing import Dict, List, Optional, Any, Tuple

from src.metrics.metrics import MetricTracker


class VSLTrainer:
    """
    Standard Trainer for Vietnamese Sign Language Recognition models.
    """
    def __init__(
        self,
        model: nn.Module,
        train_loader: torch.utils.data.DataLoader,
        val_loader: torch.utils.data.DataLoader,
        criterion: Optional[nn.Module] = None,
        optimizer: Optional[torch.optim.Optimizer] = None,
        scheduler: Optional[Any] = None,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        patience: int = 10,
        checkpoint_path: str = "checkpoints/baseline_bigru.pt",
        history_path: str = "experiments/baseline/history.json",
        device: Optional[torch.device] = None,
        use_amp: Optional[bool] = None,
        max_grad_norm: float = 1.0,
        max_batches: Optional[int] = None,
    ):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = model.to(self.device)
        self.train_loader = train_loader
        self.val_loader = val_loader

        self.criterion = criterion or nn.CrossEntropyLoss(label_smoothing=0.1)
        self.optimizer = optimizer or AdamW(
            self.model.parameters(),
            lr=lr,
            weight_decay=weight_decay,
        )
        self.scheduler = scheduler or ReduceLROnPlateau(
            self.optimizer,
            mode="min",
            factor=0.5,
            patience=5,
            min_lr=1e-6,
        )

        self.patience = patience
        self.checkpoint_path = checkpoint_path
        self.history_path = history_path
        self.max_grad_norm = max_grad_norm
        self.max_batches = max_batches

        if use_amp is None:
            self.use_amp = (self.device.type == "cuda")
        else:
            self.use_amp = use_amp and (self.device.type == "cuda")

        self.scaler = torch.amp.GradScaler("cuda", enabled=self.use_amp)

        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)

        self.best_val_loss = float("inf")
        self.best_val_top1 = 0.0
        self.best_epoch = 0
        self.patience_counter = 0
        self.history: List[Dict[str, Any]] = []

    def train_epoch(self, epoch: int) -> Dict[str, float]:
        """Trains model for one epoch."""
        self.model.train()
        tracker = MetricTracker()

        for batch_idx, batch in enumerate(self.train_loader):
            if self.max_batches is not None and batch_idx >= self.max_batches:
                break

            sequences = batch["sequences"].to(self.device, non_blocking=True)
            joint_masks = batch["joint_masks"].to(self.device, non_blocking=True)
            temporal_masks = batch["temporal_masks"].to(self.device, non_blocking=True)
            labels = batch["labels"].to(self.device, non_blocking=True)

            self.optimizer.zero_grad(set_to_none=True)

            with torch.amp.autocast("cuda", enabled=self.use_amp):
                logits = self.model(
                    sequences=sequences,
                    joint_masks=joint_masks,
                    temporal_masks=temporal_masks,
                )
                loss = self.criterion(logits, labels)

            if self.use_amp:
                self.scaler.scale(loss).backward()
                self.scaler.unscale_(self.optimizer)
                if self.max_grad_norm > 0:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                loss.backward()
                if self.max_grad_norm > 0:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                self.optimizer.step()

            tracker.update(loss.item(), logits, labels)

        return tracker.compute()

    @torch.no_grad()
    def evaluate(self, loader: torch.utils.data.DataLoader) -> Dict[str, float]:
        """Evaluates model on validation or test split."""
        self.model.eval()
        tracker = MetricTracker()

        for batch_idx, batch in enumerate(loader):
            if self.max_batches is not None and batch_idx >= self.max_batches:
                break

            sequences = batch["sequences"].to(self.device, non_blocking=True)
            joint_masks = batch["joint_masks"].to(self.device, non_blocking=True)
            temporal_masks = batch["temporal_masks"].to(self.device, non_blocking=True)
            labels = batch["labels"].to(self.device, non_blocking=True)

            with torch.amp.autocast("cuda", enabled=self.use_amp):
                logits = self.model(
                    sequences=sequences,
                    joint_masks=joint_masks,
                    temporal_masks=temporal_masks,
                )
                loss = self.criterion(logits, labels)

            tracker.update(loss.item(), logits, labels)

        return tracker.compute()

    def fit(
        self,
        epochs: int = 100,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes full training loop with early stopping and checkpointing.
        """
        if verbose:
            print(f"Starting Training: {epochs} epochs | Device: {self.device} | AMP: {self.use_amp}")
            print(f"Patience: {self.patience} | Checkpoint: {self.checkpoint_path}")

        start_time = time.perf_counter()

        for epoch in range(1, epochs + 1):
            t_epoch_start = time.perf_counter()

            train_metrics = self.train_epoch(epoch)
            val_metrics = self.evaluate(self.val_loader)
            current_lr = float(self.optimizer.param_groups[0]["lr"])

            # Step scheduler based on validation loss
            if self.scheduler is not None:
                self.scheduler.step(val_metrics["loss"])

            epoch_time = time.perf_counter() - t_epoch_start

            log_entry = {
                "epoch": epoch,
                "train_loss": train_metrics["loss"],
                "train_top1": train_metrics["top1"],
                "train_macro_f1": train_metrics["macro_f1"],
                "val_loss": val_metrics["loss"],
                "val_top1": val_metrics["top1"],
                "val_top5": val_metrics["top5"],
                "val_macro_f1": val_metrics["macro_f1"],
                "lr": current_lr,
                "time_sec": round(epoch_time, 2),
            }
            self.history.append(log_entry)

            # Checkpoint on best validation top-1 or lowest val_loss
            is_best = False
            if val_metrics["top1"] > self.best_val_top1 or (
                val_metrics["top1"] == self.best_val_top1 and val_metrics["loss"] < self.best_val_loss
            ):
                self.best_val_top1 = val_metrics["top1"]
                self.best_val_loss = val_metrics["loss"]
                self.best_epoch = epoch
                self.patience_counter = 0
                is_best = True

                torch.save({
                    "epoch": epoch,
                    "model_state_dict": self.model.state_dict(),
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "val_top1": self.best_val_top1,
                    "val_loss": self.best_val_loss,
                    "val_top5": val_metrics["top5"],
                    "val_macro_f1": val_metrics["macro_f1"],
                }, self.checkpoint_path)
            else:
                self.patience_counter += 1

            if verbose:
                best_marker = " [*BEST*]" if is_best else ""
                print(
                    f"Epoch {epoch:03d}/{epochs:03d} [{epoch_time:.1f}s] | "
                    f"Train Loss: {train_metrics['loss']:.4f}, Top1: {train_metrics['top1']:.1f}% | "
                    f"Val Loss: {val_metrics['loss']:.4f}, Top1: {val_metrics['top1']:.1f}%, F1: {val_metrics['macro_f1']:.1f}% | "
                    f"LR: {current_lr:.2e}{best_marker}"
                )

            # Save history to JSON after each epoch
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)

            # Early stopping check
            if self.patience_counter >= self.patience:
                if verbose:
                    print(f"\n[Early Stopping] No improvement for {self.patience} epochs. Stopping at epoch {epoch}.")
                break

        total_time = time.perf_counter() - start_time
        summary = {
            "total_epochs": len(self.history),
            "best_epoch": self.best_epoch,
            "best_val_top1": self.best_val_top1,
            "best_val_loss": self.best_val_loss,
            "total_time_sec": round(total_time, 2),
            "checkpoint_path": self.checkpoint_path,
            "history_path": self.history_path,
        }

        if verbose:
            print("=" * 64)
            print(f"Training Complete in {total_time/60:.2f} mins.")
            print(f"Best Model at Epoch {self.best_epoch}: Val Top-1 = {self.best_val_top1:.2f}%, Val Loss = {self.best_val_loss:.4f}")
            print(f"Saved Checkpoint: {self.checkpoint_path}")
            print("=" * 64)

        return summary
