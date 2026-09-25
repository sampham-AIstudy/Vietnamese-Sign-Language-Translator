"""
Extract CSLR predictions on S06 test set (300 samples)
using checkpoints/cslr_best.pt.
Saves to reports/cslr_s06_predictions.json.
"""

import sys
import json
from pathlib import Path
import torch
from torch.utils.data import DataLoader

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.data.vsl_gh_dataset import VSLGHContinuousDataset, VSLGlossVocabulary, vslgh_collate_fn
from src.models.cslr_stgcn_bigru import STGCNBiGRU_CSLR
from src.metrics.cslr_metrics import ctc_greedy_decode, tokens_to_words


def extract_predictions():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[EXTRACT] Running on device: {device}")

    data_root = project_root / "data" / "external" / "vsl_gh"
    vocab_path = data_root / "gloss_vocab_canonical.txt"
    ckpt_path = project_root / "checkpoints" / "cslr_best.pt"

    vocab = VSLGlossVocabulary.from_file(vocab_path)
    test_dataset = VSLGHContinuousDataset(
        canonical_json=data_root / "dataset_canonical.json",
        keypoints_dir=data_root / "keypoints_frontal",
        split="test",
        vocabulary=vocab,
        conversion_mode="semantic",
        normalize=True,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=8,
        shuffle=False,
        num_workers=0,
        collate_fn=vslgh_collate_fn,
    )

    model = STGCNBiGRU_CSLR(
        in_channels=3,
        num_joints=67,
        num_classes=len(vocab),
        hidden_size=256,
        num_gru_layers=2,
        dropout=0.3,
        pretrained_path=None,
    ).to(device)

    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    # Load canonical json to get exact translations
    with open(data_root / "dataset_canonical.json", "r", encoding="utf-8") as f:
        canonical_all = json.load(f)
    canonical_map = {item["id"]: item for item in canonical_all}

    results = []

    with torch.no_grad():
        for batch in test_loader:
            features = batch["features"].to(device)
            joint_masks = batch["joint_masks"].to(device)
            lengths = batch["lengths"].to(device)
            sample_ids = batch["sample_ids"]

            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                log_probs, out_lens = model(
                    features, joint_masks=joint_masks, sequence_lengths=lengths
                )

            pred_token_seqs = ctc_greedy_decode(
                log_probs, sequence_lengths=out_lens, blank_id=vocab.blank_id
            )
            pred_word_seqs = tokens_to_words(pred_token_seqs, vocab)

            for i, s_id in enumerate(sample_ids):
                pred_glosses = pred_word_seqs[i]
                meta = canonical_map.get(s_id, {})
                ref_glosses = meta.get("gloss_sequence", [])

                results.append({
                    "sample_id": s_id,
                    "sentence_id": meta.get("sentence_id", ""),
                    "signer_id": meta.get("signer_id", ""),
                    "ref_gloss_list": ref_glosses,
                    "ref_gloss_str": " ".join(ref_glosses),
                    "pred_gloss_list": pred_glosses,
                    "pred_gloss_str": " ".join(pred_glosses),
                    "translation": meta.get("translation", ""),
                })

    out_path = project_root / "reports" / "cslr_s06_predictions.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[EXTRACT] Saved {len(results)} sample predictions to {out_path}")
    return results


if __name__ == "__main__":
    extract_predictions()
