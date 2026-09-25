"""
CSLR Recognizer Module (Nhận diện Chuỗi Cử chỉ Liên tục từ Tọa độ Khớp Xương)

Sử dụng mô hình STGCNBiGRU_CSLR (Spatial-Temporal Graph CNN kết hợp BiGRU và CTC Loss):
- Nhận diện chuỗi cử chỉ liên tục từ dữ liệu khung xương 67 khớp (25 thân trên + 21 tay trái + 21 tay phải).
- Thực hiện giải mã CTC Greedy Decoding giải phóng các khoảng nghỉ và trùng lặp.
- Xuất ra chuỗi Glosses chuẩn bị cho mô hình dịch ViT5.
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

import torch
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.cslr_stgcn_bigru import STGCNBiGRU_CSLR
from src.data.vsl_gh_dataset import VSLGlossVocabulary
from src.metrics.cslr_metrics import ctc_greedy_decode, tokens_to_words

DEFAULT_CSLR_CKPT = PROJECT_ROOT / "checkpoints" / "cslr_best.pt"
DEFAULT_VOCAB_PATH = PROJECT_ROOT / "data" / "external" / "vsl_gh" / "gloss_vocab_canonical.txt"


class CSLRRecognizer:
    """
    Inference Engine cho bài toán Continuous Sign Language Recognition.
    """

    def __init__(
        self,
        checkpoint_path: Optional[Union[str, Path]] = None,
        vocab_path: Optional[Union[str, Path]] = None,
        device: Optional[str] = None,
        hidden_size: int = 256,
        num_gru_layers: int = 2,
    ):
        # 1. Device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # 2. Paths
        self.ckpt_path = Path(checkpoint_path) if checkpoint_path else DEFAULT_CSLR_CKPT
        self.vocab_path = Path(vocab_path) if vocab_path else DEFAULT_VOCAB_PATH

        if not self.ckpt_path.exists():
            raise FileNotFoundError(f"Không tìm thấy checkpoint CSLR tại {self.ckpt_path}")
        if not self.vocab_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file từ vựng CSLR tại {self.vocab_path}")

        # 3. Load Vocab
        self.vocab = VSLGlossVocabulary.from_file(self.vocab_path)
        self.num_classes = len(self.vocab)

        # 4. Build Model & Load Weights
        self.model = STGCNBiGRU_CSLR(
            in_channels=3,
            num_joints=67,
            num_classes=self.num_classes,
            hidden_size=hidden_size,
            num_gru_layers=num_gru_layers,
            dropout=0.0,
            pretrained_path=None,
        ).to(self.device)

        start_t = time.perf_counter()
        ckpt = torch.load(self.ckpt_path, map_location=self.device, weights_only=False)
        state_dict = ckpt.get("model_state_dict", ckpt)
        self.model.load_state_dict(state_dict)
        self.model.eval()
        self.load_duration_s = time.perf_counter() - start_t

    def predict(
        self,
        keypoints: Union[np.ndarray, torch.Tensor],
        joint_mask: Optional[Union[np.ndarray, torch.Tensor]] = None,
    ) -> Dict[str, Any]:
        """
        Dự đoán chuỗi gloss từ chuỗi khung xương.

        Args:
            keypoints: Tensor hoặc ndarray có shape [T, 67, 3] hoặc [1, T, 67, 3]
            joint_mask: Tensor hoặc ndarray có shape [T, 67] hoặc [1, T, 67]

        Returns:
            Dict chứa:
                - 'gloss_list': List[str] danh sách các từ ký hiệu dự đoán
                - 'gloss_str': Chuỗi các từ ghép bởi dấu cách
                - 'num_frames': Số lượng frame đầu vào
                - 'latency_ms': Thời gian suy luận mô hình (ms)
        """
        start_t = time.perf_counter()

        # Convert to Tensor
        if isinstance(keypoints, np.ndarray):
            kp_tensor = torch.from_numpy(keypoints).float()
        else:
            kp_tensor = keypoints.float()

        if kp_tensor.dim() == 3:
            # [T, 67, 3] -> [1, T, 67, 3]
            kp_tensor = kp_tensor.unsqueeze(0)

        num_frames = kp_tensor.size(1)
        lengths = torch.tensor([num_frames], dtype=torch.long, device=self.device)
        kp_tensor = kp_tensor.to(self.device)

        mask_tensor = None
        if joint_mask is not None:
            if isinstance(joint_mask, np.ndarray):
                mask_tensor = torch.from_numpy(joint_mask).float()
            else:
                mask_tensor = joint_mask.float()
            if mask_tensor.dim() == 2:
                mask_tensor = mask_tensor.unsqueeze(0)
            mask_tensor = mask_tensor.to(self.device)

        with torch.no_grad():
            with torch.amp.autocast("cuda", enabled=(self.device.type == "cuda")):
                log_probs, out_lens = self.model(
                    kp_tensor, joint_masks=mask_tensor, sequence_lengths=lengths
                )

        pred_token_seqs = ctc_greedy_decode(
            log_probs, sequence_lengths=out_lens, blank_id=self.vocab.blank_id
        )
        pred_word_seqs = tokens_to_words(pred_token_seqs, self.vocab)

        gloss_list = pred_word_seqs[0] if pred_word_seqs else []
        latency_ms = (time.perf_counter() - start_t) * 1000.0

        return {
            "gloss_list": gloss_list,
            "gloss_str": " ".join(gloss_list),
            "num_frames": num_frames,
            "latency_ms": round(latency_ms, 2),
        }

    def get_info(self) -> Dict[str, Any]:
        """Thông tin kỹ thuật về mô hình CSLR."""
        return {
            "checkpoint_path": str(self.ckpt_path),
            "vocab_path": str(self.vocab_path),
            "num_classes": self.num_classes,
            "device": str(self.device),
            "load_duration_s": round(self.load_duration_s, 2),
        }
