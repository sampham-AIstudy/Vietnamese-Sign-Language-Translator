"""
VSL-GH Continuous Dataset Adapter for Vietnamese Sign Language Translation (VSLT)
===================================================================================

Provides a PyTorch Dataset, landmark converter (137 -> 67), vocabulary manager,
and variable-length collate function for VSL-GH continuous sign language data.

Landmark Layout:
- VSL-GH source: [T, 411] float32 (137 MediaPipe Holistic landmarks * 3 coords)
- Converted target: [T, 67, 3] float32 (Pose 25 + Left Hand 21 + Right Hand 21)
- Optional velocity: [T, 67, 6] float32 (Position [x,y,z] + Velocity [vx,vy,vz])
- Model input contract: [B, 3, T, 67] for spatial ST-GCN encoder
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union

import numpy as np
import torch
from torch.utils.data import Dataset

logger = logging.getLogger(__name__)

# =====================================================================
# 1. LANDMARK MAPPING TABLE & CONVERSION LOGIC
# =====================================================================

"""
LANDMARK SEMANTICS INSPECTION:
-------------------------------
MediaPipe Holistic provides 33 Pose landmarks, 468 Face landmarks, 21 Left Hand, 21 Right Hand.
VSL-GH (extract_keypoints.py) extracted 137 landmarks (411 dimensions):
  - Pose: 25 landmarks (dims 0..74, 3 coords each)
    VSL-GH POSE_LANDMARKS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23, 24, 25, 26, 27, 28]
    (Note: VSL-GH skipped MP 9, 10 [mouth corners] and MP 21, 22 [thumbs], but included MP 25-28 [knees/ankles]).
  - Face: 70 landmarks (dims 75..284, 3 coords each)
    Includes lips (indices 61, 291 etc.), eyes, eyebrows, nose, face contour.
  - Left Hand: 21 landmarks (dims 285..347, 3 coords each, MP Hands 0..20)
  - Right Hand: 21 landmarks (dims 348..410, 3 coords each, MP Hands 0..20)

Current Project (CleanHolisticExtractor / QIPEDC 67 joints):
  - Pose: 25 landmarks (MediaPipe Pose 0..24 sequentially)
    0..8: Nose, eyes, ears
    9, 10: Mouth corners (mouth_left, mouth_right)
    11, 12: Shoulders (left_shoulder, right_shoulder)
    13, 14: Elbows (left_elbow, right_elbow)
    15, 16: Wrists (left_wrist, right_wrist)
    17, 18: Pinkies (left_pinky, right_pinky)
    19, 20: Indices (left_index, right_index)
    21, 22: Thumbs (left_thumb, right_thumb)
    23, 24: Hips (left_hip, right_hip)
  - Left Hand: 21 landmarks (MediaPipe Hands 0..20 -> joints 25..45)
  - Right Hand: 21 landmarks (MediaPipe Hands 0..20 -> joints 46..66)

Hand landmark ordering is 100% identical between VSL-GH and current project (LH: 21, RH: 21).

Two conversion modes are provided:
1. 'direct': Extracts VSL-GH's 25 pose landmarks + 21 LH + 21 RH. (Preserves VSL-GH native 25 pose landmarks).
2. 'semantic': Remaps VSL-GH landmarks to exact QIPEDC 67-joint anatomical graph:
   - MP 0..8 from VSL-GH pose 0..8
   - MP 9, 10 (mouth) from VSL-GH face landmarks (FaceMesh 61, 291 at face indices 0 and 10)
   - MP 11..20 (shoulders, elbows, wrists, pinkies, indices) from VSL-GH pose 9..18
   - MP 21, 22 (pose thumbs) from Left Hand tip (joint 4) and Right Hand tip (joint 4)
   - MP 23, 24 (hips) from VSL-GH pose 19, 20
   - Left Hand (21) from VSL-GH LH (dims 285..348)
   - Right Hand (21) from VSL-GH RH (dims 348..411)
"""

# Explicit Landmark Mapping Table for Documentation & Verification
LANDMARK_MAPPING_TABLE = {
    "direct_mode": {
        "pose_slice": slice(0, 75),       # 25 landmarks * 3 = 75
        "face_slice": slice(75, 285),     # 70 landmarks * 3 = 210 (omitted from 67 joints)
        "lh_slice": slice(285, 348),      # 21 landmarks * 3 = 63
        "rh_slice": slice(348, 411),      # 21 landmarks * 3 = 63
        "output_joints": 67,
        "output_coords": 201,
    },
    "semantic_mode": {
        "qipedc_joint_sources": {
            0: ("pose", 0),   # Nose
            1: ("pose", 1),   # Left eye inner
            2: ("pose", 2),   # Left eye
            3: ("pose", 3),   # Left eye outer
            4: ("pose", 4),   # Right eye inner
            5: ("pose", 5),   # Right eye
            6: ("pose", 6),   # Right eye outer
            7: ("pose", 7),   # Left ear
            8: ("pose", 8),   # Right ear
            9: ("face", 0),   # Mouth left (FaceMesh 61)
            10: ("face", 10), # Mouth right (FaceMesh 291)
            11: ("pose", 9),  # Left shoulder (MP 11)
            12: ("pose", 10), # Right shoulder (MP 12)
            13: ("pose", 11), # Left elbow (MP 13)
            14: ("pose", 12), # Right elbow (MP 14)
            15: ("pose", 13), # Left wrist (MP 15)
            16: ("pose", 14), # Right wrist (MP 16)
            17: ("pose", 15), # Left pinky (MP 17)
            18: ("pose", 16), # Right pinky (MP 18)
            19: ("pose", 17), # Left index (MP 19)
            20: ("pose", 18), # Right index (MP 20)
            21: ("lh", 4),    # Left thumb tip (LH 4)
            22: ("rh", 4),    # Right thumb tip (RH 4)
            23: ("pose", 19), # Left hip (MP 23)
            24: ("pose", 20), # Right hip (MP 24)
        }
    }
}


def convert_137_to_67(keypoints_137: np.ndarray, mode: str = "semantic") -> np.ndarray:
    """
    Converts VSL-GH 137-landmark representation [T, 411] to project 67-joint representation [T, 67, 3].

    Args:
        keypoints_137: np.ndarray of shape [T, 411] or [411], dtype float32.
        mode: 'direct' or 'semantic'.
            - 'direct': Extracts Pose [0..24] (75 dims) + LH [0..20] (63 dims) + RH [0..20] (63 dims).
            - 'semantic': Anatomically remaps to match QIPEDC graph topology (using face mouth corners & hand thumb tips).

    Returns:
        np.ndarray of shape [T, 67, 3], dtype float32.
    """
    is_1d = (keypoints_137.ndim == 1)
    if is_1d:
        keypoints_137 = keypoints_137[np.newaxis, :]

    if keypoints_137.shape[1] != 411:
        raise ValueError(f"Expected 411 input features (137 landmarks x 3), got shape {keypoints_137.shape}")

    T = keypoints_137.shape[0]

    if mode == "direct":
        # Pose: 25 landmarks (dims 0..75) -> [T, 25, 3]
        pose = keypoints_137[:, 0:75].reshape(T, 25, 3)
        # Left Hand: 21 landmarks (dims 285..348) -> [T, 21, 3]
        lh = keypoints_137[:, 285:348].reshape(T, 21, 3)
        # Right Hand: 21 landmarks (dims 348..411) -> [T, 21, 3]
        rh = keypoints_137[:, 348:411].reshape(T, 21, 3)
        out = np.concatenate([pose, lh, rh], axis=1).astype(np.float32)

    elif mode == "semantic":
        out = np.zeros((T, 67, 3), dtype=np.float32)
        pose_all = keypoints_137[:, 0:75].reshape(T, 25, 3)
        face_all = keypoints_137[:, 75:285].reshape(T, 70, 3)
        lh_all   = keypoints_137[:, 285:348].reshape(T, 21, 3)
        rh_all   = keypoints_137[:, 348:411].reshape(T, 21, 3)

        src_map = LANDMARK_MAPPING_TABLE["semantic_mode"]["qipedc_joint_sources"]
        for j_idx, (src_type, src_idx) in src_map.items():
            if src_type == "pose":
                out[:, j_idx] = pose_all[:, src_idx]
            elif src_type == "face":
                out[:, j_idx] = face_all[:, src_idx]
            elif src_type == "lh":
                out[:, j_idx] = lh_all[:, src_idx]
            elif src_type == "rh":
                out[:, j_idx] = rh_all[:, src_idx]

        # Hands are identical
        out[:, 25:46] = lh_all
        out[:, 46:67] = rh_all

    else:
        raise ValueError(f"Unknown conversion mode '{mode}'. Choose 'direct' or 'semantic'.")

    if is_1d:
        out = out[0]

    return out


def compute_velocity(coords: np.ndarray) -> np.ndarray:
    """
    Computes first-order backward difference velocity for landmark trajectory:
      v[0] = 0
      v[t] = coords[t] - coords[t-1]  for t >= 1

    Args:
        coords: [T, 67, 3] float32

    Returns:
        velocity: [T, 67, 3] float32
    """
    T = coords.shape[0]
    vel = np.zeros_like(coords, dtype=np.float32)
    if T > 1:
        vel[1:] = coords[1:] - coords[:-1]
    return vel


# =====================================================================
# 2. GLOSS VOCABULARY
# =====================================================================

class VSLGlossVocabulary:
    """
    Gloss Vocabulary Manager for Continuous VSL Translation (CTC).
    Maintains explicit:
      - blank_index = 0 (<blank>)
      - unk_index = 1 (<unk>)
      - target gloss tokens (sorted)
    """

    def __init__(
        self,
        tokens: Optional[List[str]] = None,
        blank_token: str = "<blank>",
        unk_token: str = "<unk>",
        handle_unknown: str = "unk",  # 'unk' or 'error'
    ):
        self.blank_token = blank_token
        self.unk_token = unk_token
        self.handle_unknown = handle_unknown

        self.gloss_to_id: Dict[str, int] = {}
        self.id_to_gloss: Dict[int, str] = {}

        if tokens is not None:
            self._build_vocab(tokens)

    def _build_vocab(self, tokens: List[str]):
        # Ensure blank is at 0, unk is at 1
        specials = [self.blank_token, self.unk_token]
        target_tokens = [t for t in sorted(list(set(tokens))) if t not in specials]

        all_tokens = specials + target_tokens
        self.gloss_to_id = {tok: idx for idx, tok in enumerate(all_tokens)}
        self.id_to_gloss = {idx: tok for idx, tok in enumerate(all_tokens)}

    @property
    def blank_id(self) -> int:
        return self.gloss_to_id[self.blank_token]

    @property
    def unk_id(self) -> int:
        return self.gloss_to_id[self.unk_token]

    def encode(self, gloss_sequence: List[str]) -> List[int]:
        """Encodes list of gloss strings into integer IDs."""
        ids = []
        for g in gloss_sequence:
            g_clean = g.strip()
            if not g_clean:
                continue
            if g_clean in self.gloss_to_id:
                ids.append(self.gloss_to_id[g_clean])
            elif self.handle_unknown == "unk":
                ids.append(self.unk_id)
            else:
                raise KeyError(f"Unknown gloss '{g_clean}' not in vocabulary.")
        return ids

    def decode(self, ids: List[int], remove_blank: bool = True) -> List[str]:
        """Decodes list of integer IDs back to gloss strings."""
        glosses = []
        for i in ids:
            if remove_blank and i == self.blank_id:
                continue
            glosses.append(self.id_to_gloss.get(i, self.unk_token))
        return glosses

    def __len__(self) -> int:
        return len(self.gloss_to_id)

    @classmethod
    def from_file(cls, vocab_path: Union[str, Path], handle_unknown: str = "unk") -> "VSLGlossVocabulary":
        """Loads vocabulary from file (one token per line)."""
        lines = Path(vocab_path).read_text(encoding="utf-8").splitlines()
        tokens = [line.strip() for line in lines if line.strip()]
        return cls(tokens=tokens, handle_unknown=handle_unknown)

    @classmethod
    def from_canonical_dataset(cls, dataset_json_path: Union[str, Path], handle_unknown: str = "unk") -> "VSLGlossVocabulary":
        """Extracts unique glosses from canonical metadata JSON."""
        with open(dataset_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_glosses = set()
        for item in data:
            for g in item.get("gloss_sequence", []):
                g_clean = g.strip()
                if g_clean:
                    all_glosses.add(g_clean)
        return cls(tokens=list(all_glosses), handle_unknown=handle_unknown)

    def save(self, vocab_path: Union[str, Path]):
        """Saves vocabulary to a text file (one token per line)."""
        with open(vocab_path, "w", encoding="utf-8") as f:
            for i in range(len(self)):
                f.write(self.id_to_gloss[i] + "\n")


# =====================================================================
# 3. TEMPORAL TIMESTAMP -> FRAME MAPPING
# =====================================================================

def time_str_to_ms(t_str: str) -> float:
    """Parses 'HH:MM:SS.mmm' into millisecond float."""
    try:
        parts = t_str.strip().split(":")
        h = int(parts[0])
        m = int(parts[1])
        s = float(parts[2])
        return (h * 3600 + m * 60 + s) * 1000.0
    except Exception:
        return 0.0


def map_temporal_boundary(
    start_time_str: str,
    end_time_str: str,
    fps: float,
    total_frames: int,
) -> Tuple[float, float, int, int]:
    """
    Deterministic conversion of time string boundaries to frame indices:
      start_ms = time_to_ms(start_time_str)
      end_ms   = time_to_ms(end_time_str)
      start_frame = clip(round(start_ms * fps / 1000), 0, total_frames)
      end_frame   = clip(round(end_ms * fps / 1000), start_frame, total_frames)

    Returns:
        (start_ms, end_ms, start_frame, end_frame)
    """
    start_ms = time_str_to_ms(start_time_str)
    end_ms = time_str_to_ms(end_time_str)

    start_frame = int(round(start_ms * fps / 1000.0))
    end_frame   = int(round(end_ms * fps / 1000.0))

    start_frame = max(0, min(total_frames, start_frame))
    end_frame   = max(start_frame, min(total_frames, end_frame))

    return start_ms, end_ms, start_frame, end_frame


# =====================================================================
# 4. CONTINUOUS DATASET CLASS
# =====================================================================

class VSLGHContinuousDataset(Dataset):
    """
    Continuous Sign Language Recognition & Translation Dataset for VSL-GH.

    Reads:
      data/external/vsl_gh/dataset_canonical.json
    Loads:
      data/external/vsl_gh/keypoints_frontal/
    """

    def __init__(
        self,
        canonical_json: Union[str, Path] = "data/external/vsl_gh/dataset_canonical.json",
        keypoints_dir: Union[str, Path] = "data/external/vsl_gh/keypoints_frontal",
        split: Optional[str] = None,  # 'train', 'val', 'test', or None (all)
        loso_signer: Optional[str] = None,  # e.g. 'S01'..'S06'
        loso_mode: Optional[str] = None,    # 'train' or 'test'
        vocabulary: Optional[VSLGlossVocabulary] = None,
        conversion_mode: str = "semantic",     # 'direct' or 'semantic'
        use_velocity: bool = False,
        normalize: bool = False,
        max_frames: Optional[int] = None,
        truncation: bool = False,
        temporal_subsample: int = 1,
    ):
        self.canonical_json = Path(canonical_json)
        self.keypoints_dir = Path(keypoints_dir)
        self.split = split
        self.loso_signer = loso_signer
        self.loso_mode = loso_mode
        self.conversion_mode = conversion_mode
        self.use_velocity = use_velocity
        self.normalize = normalize
        self.max_frames = max_frames
        self.truncation = truncation
        self.temporal_subsample = max(1, int(temporal_subsample))

        if not self.canonical_json.exists():
            raise FileNotFoundError(f"Canonical metadata not found: {self.canonical_json}")
        if not self.keypoints_dir.exists():
            raise FileNotFoundError(f"Keypoints directory not found: {self.keypoints_dir}")

        with open(self.canonical_json, "r", encoding="utf-8") as f:
            all_samples = json.load(f)

        # Filter by split or LOSO
        self.samples = self._filter_samples(all_samples)

        # Set up vocabulary
        if vocabulary is not None:
            self.vocab = vocabulary
        else:
            # Build directly from canonical dataset to ensure 100% token coverage
            self.vocab = VSLGlossVocabulary.from_canonical_dataset(self.canonical_json)

    def _filter_samples(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered = []
        for s in samples:
            signer = s.get("signer_id", "")
            s_split = s.get("split", "")

            # 1. Standard train/val/test filter
            if self.split is not None:
                if s_split != self.split:
                    continue

            # 2. LOSO filter
            if self.loso_signer is not None and self.loso_mode is not None:
                if self.loso_mode == "test":
                    if signer != self.loso_signer:
                        continue
                elif self.loso_mode == "train":
                    if signer == self.loso_signer:
                        continue

            filtered.append(s)
        return filtered

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        meta = self.samples[idx]
        sample_id = meta["id"]

        # 1. Load frontal keypoints [T, 411]
        kp_filename = f"{sample_id}.npy"
        kp_path = self.keypoints_dir / kp_filename
        if not kp_path.exists():
            # Fallback to keypoint_file path stored in metadata
            kp_path = Path("data/external/vsl_gh") / meta.get("keypoint_file", "")
            if not kp_path.exists():
                raise FileNotFoundError(f"Keypoint file not found for sample {sample_id} at {kp_path}")

        raw_kps_137 = np.load(kp_path).astype(np.float32)  # [T, 411]
        raw_T = raw_kps_137.shape[0]

        # 2. Convert [T, 411] -> [T, 67, 3]
        kps_67 = convert_137_to_67(raw_kps_137, mode=self.conversion_mode)  # [T, 67, 3]

        # 3. Compute joint presence mask: 1.0 if joint detected (norm > 1e-6), 0.0 if missing
        joint_mask = (np.abs(kps_67).sum(axis=-1) > 1e-6).astype(np.float32)  # [T, 67]

        # 4. Optional spatial normalization (shoulder centering + shoulder width scale)
        if self.normalize:
            # Pose shoulders: in direct mode index 9 & 10; in semantic mode index 11 & 12
            ls_idx = 11 if self.conversion_mode == "semantic" else 9
            rs_idx = 12 if self.conversion_mode == "semantic" else 10
            both_shoulders = (joint_mask[:, ls_idx] > 0.5) & (joint_mask[:, rs_idx] > 0.5)
            if np.any(both_shoulders):
                center = 0.5 * (kps_67[:, ls_idx] + kps_67[:, rs_idx])  # [T, 3]
                diffs = kps_67[both_shoulders, ls_idx] - kps_67[both_shoulders, rs_idx]
                scale = float(np.median(np.linalg.norm(diffs, axis=-1)))
                if scale > 1e-5:
                    kps_67 = (kps_67 - center[:, np.newaxis, :]) / scale

        # 5. Optional temporal subsampling
        if self.temporal_subsample > 1:
            kps_67 = kps_67[::self.temporal_subsample]
            joint_mask = joint_mask[::self.temporal_subsample]

        # 6. Optional max_frames truncation
        T_cur = kps_67.shape[0]
        if self.truncation and self.max_frames is not None and T_cur > self.max_frames:
            kps_67 = kps_67[:self.max_frames]
            joint_mask = joint_mask[:self.max_frames]
            T_cur = self.max_frames

        # 7. Optional velocity features: [T, 67, 3] -> [T, 67, 6]
        if self.use_velocity:
            vel = compute_velocity(kps_67)
            features = np.concatenate([kps_67, vel], axis=-1)  # [T, 67, 6]
        else:
            features = kps_67  # [T, 67, 3]

        # 8. Temporal annotations & Frame conversion
        fps = float(meta.get("fps", 30.0))
        gloss_details_processed = []
        for g in meta.get("glosses_detail", []):
            st_ms, et_ms, st_frame, et_frame = map_temporal_boundary(
                start_time_str=g.get("start_time", "00:00:00.000"),
                end_time_str=g.get("end_time", "00:00:00.000"),
                fps=fps,
                total_frames=raw_T,
            )
            # Adjust frame indices if subsampled
            if self.temporal_subsample > 1:
                st_frame = st_frame // self.temporal_subsample
                et_frame = et_frame // self.temporal_subsample

            gloss_details_processed.append({
                "gloss": g.get("gloss", ""),
                "start_ms": st_ms,
                "end_ms": et_ms,
                "start_frame": st_frame,
                "end_frame": et_frame,
            })

        gloss_seq = meta.get("gloss_sequence", [])
        gloss_ids = self.vocab.encode(gloss_seq)

        return {
            "sample_id": sample_id,
            "sentence_id": meta.get("sentence_id", ""),
            "signer_id": meta.get("signer_id", ""),
            "repetition": meta.get("repetition", ""),
            "split": meta.get("split", ""),
            "duration_sec": float(meta.get("duration_sec", 0.0)),
            "raw_length": raw_T,
            "length": T_cur,
            "keypoints": torch.tensor(features, dtype=torch.float32),
            "joint_mask": torch.tensor(joint_mask, dtype=torch.float32),
            "gloss_sequence": gloss_seq,
            "gloss_ids": torch.tensor(gloss_ids, dtype=torch.long),
            "gloss_details": gloss_details_processed,
            "gloss_frame_boundaries": meta.get("gloss_frame_boundaries", []),
            "translation": meta.get("translation", ""),
            "annotation_source": meta.get("annotation_source", "source"),
        }


# =====================================================================
# 5. COLLATE FUNCTION FOR VARIABLE-LENGTH BATCHES
# =====================================================================

def vslgh_collate_fn(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Collate function supporting variable-length temporal sequences and CTC targets.

    Args:
        batch: List of sample dictionaries from VSLGHContinuousDataset.

    Returns:
        Dictionary containing:
          - 'features': [B, max_T, 67, C] float32 tensor (zero-padded)
          - 'features_stgcn': [B, C, max_T, 67] float32 tensor (ready for ST-GCN spatial encoder)
          - 'joint_masks': [B, max_T, 67] float32 tensor (zero-padded)
          - 'temporal_masks': [B, max_T] float32 tensor (1.0 for valid frames, 0.0 for padded)
          - 'lengths': [B] long tensor of frame lengths
          - 'gloss_targets': 1D long tensor of concatenated target gloss IDs for PyTorch nn.CTCLoss
          - 'gloss_targets_padded': [B, max_gloss_len] long tensor (padded with blank_id=0)
          - 'gloss_lengths': [B] long tensor of gloss sequence lengths
          - 'sample_ids': List[str] of length B
          - 'translations': List[str] of length B
          - 'annotation_sources': List[str] of length B
    """
    B = len(batch)
    lengths = [item["length"] for item in batch]
    max_T = max(lengths)
    num_joints = batch[0]["keypoints"].shape[1]  # 67
    num_channels = batch[0]["keypoints"].shape[2] # 3 or 6

    # 1. Pad Keypoint Sequences & Masks
    padded_features = torch.zeros((B, max_T, num_joints, num_channels), dtype=torch.float32)
    padded_joint_masks = torch.zeros((B, max_T, num_joints), dtype=torch.float32)
    temporal_masks = torch.zeros((B, max_T), dtype=torch.float32)

    for i, item in enumerate(batch):
        T_i = item["length"]
        padded_features[i, :T_i] = item["keypoints"]
        padded_joint_masks[i, :T_i] = item["joint_mask"]
        temporal_masks[i, :T_i] = 1.0

    # 2. Form Layout for ST-GCN: [B, max_T, 67, C] -> [B, C, max_T, 67]
    features_stgcn = padded_features.permute(0, 3, 1, 2).contiguous()

    # 3. Collate Gloss Targets for CTC
    gloss_lengths = [len(item["gloss_ids"]) for item in batch]
    max_gloss_len = max(max(gloss_lengths), 1)

    # 1D concatenated targets for standard PyTorch CTCLoss
    concatenated_targets = torch.cat([item["gloss_ids"] for item in batch], dim=0)

    # 2D padded targets
    padded_gloss_targets = torch.zeros((B, max_gloss_len), dtype=torch.long)
    for i, item in enumerate(batch):
        g_len = len(item["gloss_ids"])
        if g_len > 0:
            padded_gloss_targets[i, :g_len] = item["gloss_ids"]

    return {
        "features": padded_features,                          # [B, max_T, 67, C]
        "features_stgcn": features_stgcn,                    # [B, C, max_T, 67]
        "joint_masks": padded_joint_masks,                    # [B, max_T, 67]
        "temporal_masks": temporal_masks,                     # [B, max_T]
        "lengths": torch.tensor(lengths, dtype=torch.long),  # [B]
        "gloss_targets": concatenated_targets,                # [sum(gloss_lengths)]
        "gloss_targets_padded": padded_gloss_targets,         # [B, max_gloss_len]
        "gloss_lengths": torch.tensor(gloss_lengths, dtype=torch.long), # [B]
        "sample_ids": [item["sample_id"] for item in batch],
        "translations": [item["translation"] for item in batch],
        "annotation_sources": [item["annotation_source"] for item in batch],
    }
