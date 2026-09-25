"""
VSL Translator Engine (Phần lõi Dịch thuật Ký hiệu sang Tiếng Việt Tự nhiên)

Sử dụng mô hình seq2seq VietAI/vit5-base đã được tinh chỉnh qua 2 giai đoạn:
- Giai đoạn 1: Pretrain trên 10K ngữ liệu song ngữ tiếng Việt - VSL.
- Giai đoạn 2: Fine-tune trên tập câu chuẩn VSL-GH.

Nhiệm vụ:
- Chuẩn hóa chuỗi ký hiệu đầu vào (ALL-CAPS, hyphenated tokens, danh sách từ).
- Sinh câu tiếng Việt tự nhiên hoàn chỉnh (đúng ngữ pháp, có dấu thanh, viết hoa đầu câu, dấu chấm câu).
- Tối ưu hóa suy luận (Beam Search / Greedy Decoding, FP16 Autocast trên GPU).
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.translation.text_normalizer import normalize_vsl_source, normalize_vietnamese_target

DEFAULT_CHECKPOINT = PROJECT_ROOT / "checkpoints" / "vit5_stage2" / "best_model"
FALLBACK_CHECKPOINT = PROJECT_ROOT / "checkpoints" / "vit5_stage1" / "best_model"


class VSLTranslator:
    """
    Công cụ dịch thuật VSL Gloss -> Tiếng Việt tự nhiên.
    Hỗ trợ chế độ đơn lẻ và xử lý theo lô (batch processing).
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        device: Optional[str] = None,
        num_beams: int = 4,
        max_length: int = 64,
        use_fp16: bool = True,
    ):
        self.num_beams = num_beams
        self.max_length = max_length

        # 1. Xác định thiết bị tính toán
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.use_fp16 = use_fp16 and (self.device.type == "cuda")

        # 2. Xác định đường dẫn trọng số
        if model_path is not None:
            self.model_path = Path(model_path)
        elif DEFAULT_CHECKPOINT.exists():
            self.model_path = DEFAULT_CHECKPOINT
        elif FALLBACK_CHECKPOINT.exists():
            self.model_path = FALLBACK_CHECKPOINT
        else:
            raise FileNotFoundError(
                f"Không tìm thấy checkpoint ViT5 tại {DEFAULT_CHECKPOINT} hoặc {FALLBACK_CHECKPOINT}."
            )

        # 3. Nạp Tokenizer và Model
        self._load_model()

    def _load_model(self):
        start_time = time.perf_counter()
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
        self.model = AutoModelForSeq2SeqLM.from_pretrained(str(self.model_path)).to(self.device)
        self.model.eval()

        self.param_count = sum(p.numel() for p in self.model.parameters())
        self.load_duration_s = time.perf_counter() - start_time

    def translate(
        self,
        gloss_input: Union[str, List[str]],
        num_beams: Optional[int] = None,
        max_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Dịch một chuỗi hoặc danh sách các gloss sang câu tiếng Việt tự nhiên.

        Args:
            gloss_input: Chuỗi hoặc danh sách từ (ví dụ: ["BẠN", "TÊN", "GÌ"] hoặc "bạn tên gì")
            num_beams: Số tia beam search (mặc định theo cấu hình khởi tạo)
            max_length: Độ dài tối đa của câu sinh ra

        Returns:
            Dict chứa:
                - 'source_raw': Đầu vào nguyên bản
                - 'source_normalized': Chuỗi nguồn sau chuẩn hóa
                - 'translation': Câu tiếng Việt tự nhiên
                - 'latency_ms': Thời gian suy luận tính bằng ms
        """
        if not gloss_input:
            return {
                "source_raw": gloss_input,
                "source_normalized": "",
                "translation": "",
                "latency_ms": 0.0,
            }

        start_time = time.perf_counter()
        beams = num_beams if num_beams is not None else self.num_beams
        max_len = max_length if max_length is not None else self.max_length

        # Chuẩn hóa đầu vào
        normalized_src = normalize_vsl_source(gloss_input)
        if not normalized_src:
            return {
                "source_raw": gloss_input,
                "source_normalized": "",
                "translation": "",
                "latency_ms": 0.0,
            }

        inputs = self.tokenizer(
            normalized_src,
            max_length=128,
            padding=False,
            truncation=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            with torch.amp.autocast("cuda", enabled=self.use_fp16):
                outputs = self.model.generate(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    num_beams=beams,
                    max_length=max_len,
                    no_repeat_ngram_size=2,
                    length_penalty=1.0,
                    early_stopping=True,
                )

        raw_pred = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        translation = normalize_vietnamese_target(raw_pred)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "source_raw": gloss_input,
            "source_normalized": normalized_src,
            "translation": translation,
            "latency_ms": round(latency_ms, 2),
        }

    def translate_batch(
        self,
        batch_inputs: List[Union[str, List[str]]],
        batch_size: int = 16,
        num_beams: Optional[int] = None,
        max_length: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Dịch nhiều câu cùng lúc với kỹ thuật gom lô."""
        if not batch_inputs:
            return []

        beams = num_beams if num_beams is not None else self.num_beams
        max_len = max_length if max_length is not None else self.max_length
        results = []

        normalized_sources = [normalize_vsl_source(item) for item in batch_inputs]

        for i in range(0, len(normalized_sources), batch_size):
            chunk_srcs = normalized_sources[i : i + batch_size]
            chunk_raws = batch_inputs[i : i + batch_size]

            valid_indices = [idx for idx, s in enumerate(chunk_srcs) if s.strip()]
            valid_srcs = [chunk_srcs[idx] for idx in valid_indices]

            if not valid_srcs:
                for raw_in in chunk_raws:
                    results.append({
                        "source_raw": raw_in,
                        "source_normalized": "",
                        "translation": "",
                        "latency_ms": 0.0,
                    })
                continue

            start_t = time.perf_counter()
            inputs = self.tokenizer(
                valid_srcs,
                max_length=128,
                padding=True,
                truncation=True,
                return_tensors="pt",
            ).to(self.device)

            with torch.no_grad():
                with torch.amp.autocast("cuda", enabled=self.use_fp16):
                    outputs = self.model.generate(
                        input_ids=inputs["input_ids"],
                        attention_mask=inputs["attention_mask"],
                        num_beams=beams,
                        max_length=max_len,
                        no_repeat_ngram_size=2,
                        length_penalty=1.0,
                        early_stopping=True,
                    )

            batch_preds = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
            batch_latency = (time.perf_counter() - start_t) * 1000.0 / len(valid_srcs)

            res_map = {}
            for v_idx, pred in zip(valid_indices, batch_preds):
                res_map[v_idx] = normalize_vietnamese_target(pred)

            for idx, (raw_in, norm_s) in enumerate(zip(chunk_raws, chunk_srcs)):
                results.append({
                    "source_raw": raw_in,
                    "source_normalized": norm_s,
                    "translation": res_map.get(idx, ""),
                    "latency_ms": round(batch_latency, 2),
                })

        return results

    def get_info(self) -> Dict[str, Any]:
        """Trả về thông số kỹ thuật của mô hình dịch thuật."""
        return {
            "model_path": str(self.model_path),
            "architecture": "VietAI/vit5-base (Seq2Seq Transformer)",
            "total_parameters": self.param_count,
            "device": str(self.device),
            "fp16_enabled": self.use_fp16,
            "num_beams": self.num_beams,
            "max_length": self.max_length,
            "load_duration_s": round(self.load_duration_s, 2),
        }
