"""
Standalone evaluation script to reproduce CSLR Test WER on S06.
Model: checkpoints/cslr_best.pt
Data: data/external/vsl_gh
Test Signer: S06 (300 samples)
"""

import sys
import json
from pathlib import Path
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.data.vsl_gh_dataset import VSLGHContinuousDataset, VSLGlossVocabulary, vslgh_collate_fn
from src.models.cslr_stgcn_bigru import STGCNBiGRU_CSLR
from src.training.train_cslr import evaluate_cslr


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[EVAL] Evaluating on device: {device}")

    data_root = project_root / "data" / "external" / "vsl_gh"
    vocab_path = data_root / "gloss_vocab_canonical.txt"
    ckpt_path = project_root / "checkpoints" / "cslr_best.pt"

    if not ckpt_path.is_file():
        print(f"[ERROR] Checkpoint not found at: {ckpt_path}")
        return

    vocab = VSLGlossVocabulary.from_file(vocab_path)
    print(f"[EVAL] Vocabulary size: {len(vocab)} (including blank at index 0)")

    test_dataset = VSLGHContinuousDataset(
        canonical_json=data_root / "dataset_canonical.json",
        keypoints_dir=data_root / "keypoints_frontal",
        split="test",
        vocabulary=vocab,
        conversion_mode="semantic",
        normalize=True,
    )
    print(f"[EVAL] Test samples (S06): {len(test_dataset)}")

    test_loader = DataLoader(
        test_dataset,
        batch_size=8,
        shuffle=False,
        num_workers=0,
        collate_fn=vslgh_collate_fn,
    )

    # Initialize model
    model = STGCNBiGRU_CSLR(
        in_channels=3,
        num_joints=67,
        num_classes=len(vocab),
        hidden_size=256,
        num_gru_layers=2,
        dropout=0.3,
        pretrained_path=None,
    ).to(device)

    # Load checkpoint
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    print(f"[EVAL] Successfully loaded checkpoint from {ckpt_path}")
    if "best_val_WER" in ckpt:
        print(f"[EVAL] Checkpoint best_val_WER: {ckpt['best_val_WER']:.2f}%")

    ctc_loss_fn = nn.CTCLoss(blank=0, zero_infinity=True)

    print("[EVAL] Running evaluation over test set (S06)...")
    res = evaluate_cslr(model, test_loader, ctc_loss_fn, vocab, device, max_examples=5)

    print("\n" + "=" * 60)
    print(f"TEST EVALUATION RESULT (S06 Held-Out Signer):")
    print(f"  Total Samples: {res['total_samples']}")
    print(f"  Test WER: {res['wer']:.2f}%")
    print(f"  Substitutions: {res['substitutions']} ({res['sub_rate']:.2f}%)")
    print(f"  Deletions:     {res['deletions']} ({res['del_rate']:.2f}%)")
    print(f"  Insertions:    {res['insertions']} ({res['ins_rate']:.2f}%)")
    print(f"  Total Ref Words: {res['total_ref_words']}")
    print(f"  Total Hyp Words: {res['total_hyp_words']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
