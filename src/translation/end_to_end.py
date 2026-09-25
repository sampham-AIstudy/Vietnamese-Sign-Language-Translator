"""
VSL End-to-End Translator (Pipeline Lõi Hợp Nhất Toàn Diện)

Tích hợp 3 phân hệ cốt lõi:
1. Continuous Sign Language Recognition (CSLR - ST-GCN + BiGRU):
   Biến đổi chuỗi tọa độ khung xương 67 khớp thành chuỗi Gloss cử chỉ.
2. Sign-to-Text Translation (ViT5 Seq2Seq):
   Chuyển đổi chuỗi Gloss thành câu văn tiếng Việt tự nhiên hoàn chỉnh, có dấu thanh và ngữ pháp chuẩn.
3. VSL Lexicon Bank:
   Tra cứu đối sánh video ký hiệu chuẩn (4,797 video, 8 phương ngữ vùng miền) cho các từ trong bản dịch.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.translation.translator import VSLTranslator
from src.translation.cslr_recognizer import CSLRRecognizer
from src.data.lexicon_bank import VSLLexiconBank


class VSLEndToEndTranslator:
    """
    Bộ điều phối toàn diện cho hệ thống Dịch Ngôn ngữ Ký hiệu Việt Nam.
    """

    def __init__(
        self,
        vit5_path: Optional[Union[str, Path]] = None,
        cslr_ckpt_path: Optional[Union[str, Path]] = None,
        cslr_vocab_path: Optional[Union[str, Path]] = None,
        device: Optional[str] = None,
        load_cslr: bool = True,
        load_lexicon: bool = True,
    ):
        # 1. Device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        start_t = time.perf_counter()

        # 2. Translation Engine (ViT5) - Luôn bắt buộc
        self.translator = VSLTranslator(model_path=vit5_path, device=self.device)

        # 3. CSLR Recognizer (ST-GCN + BiGRU) - Tùy chọn
        self.cslr: Optional[CSLRRecognizer] = None
        if load_cslr:
            try:
                self.cslr = CSLRRecognizer(
                    checkpoint_path=cslr_ckpt_path,
                    vocab_path=cslr_vocab_path,
                    device=self.device,
                )
            except Exception as e:
                print(f"[CẢNH BÁO] Không thể nạp CSLRRecognizer: {e}")

        # 4. Lexicon Bank (Ngân hàng từ điển 8 phương ngữ) - Tùy chọn
        self.lexicon: Optional[VSLLexiconBank] = None
        if load_lexicon:
            try:
                self.lexicon = VSLLexiconBank()
            except Exception as e:
                print(f"[CẢNH BÁO] Không thể nạp VSLLexiconBank: {e}")

        self.init_duration_s = time.perf_counter() - start_t

    def translate_glosses(
        self,
        gloss_input: Union[str, List[str]],
        attach_lexicon: bool = True,
    ) -> Dict[str, Any]:
        """
        Dịch chuỗi từ ký hiệu sang câu tiếng Việt tự nhiên và tìm video đối sánh.

        Args:
            gloss_input: Danh sách hoặc chuỗi các từ (ví dụ: ["BẠN", "TÊN", "GÌ"])
            attach_lexicon: Nếu True, tự động tìm kiếm video ký hiệu mẫu từ từ điển

        Returns:
            Dict kết quả dịch thuật và video đối chiếu
        """
        trans_res = self.translator.translate(gloss_input)

        lexicon_matches = {}
        if attach_lexicon and self.lexicon:
            tokens = []
            if isinstance(gloss_input, (list, tuple)):
                tokens = [str(t).strip().lower() for t in gloss_input]
            else:
                tokens = str(gloss_input).strip().lower().split()

            for tok in tokens:
                matches = self.lexicon.get_by_gloss(tok, exact=False)
                if matches:
                    lexicon_matches[tok] = [
                        {
                            "id": m.get("id"),
                            "gloss": m.get("gloss"),
                            "region": m.get("region"),
                            "category": m.get("category"),
                            "video_filename": m.get("video_filename"),
                            "file_path": m.get("file_path"),
                        }
                        for m in matches[:3]
                    ]

        return {
            "source_raw": trans_res["source_raw"],
            "source_normalized": trans_res["source_normalized"],
            "translation": trans_res["translation"],
            "latency_ms": trans_res["latency_ms"],
            "lexicon_matches": lexicon_matches,
        }

    def translate_keypoints(
        self,
        keypoints: Union[np.ndarray, torch.Tensor],
        joint_mask: Optional[Union[np.ndarray, torch.Tensor]] = None,
        attach_lexicon: bool = True,
    ) -> Dict[str, Any]:
        """
        Dịch chuỗi tọa độ khung xương 67 khớp trực tiếp sang câu tiếng Việt hoàn chỉnh.
        Luồng: Keypoints [T, 67, 3] -> CSLR ST-GCN -> Predicted Glosses -> ViT5 -> Tiếng Việt.
        """
        if self.cslr is None:
            raise RuntimeError("CSLR Recognizer chưa được nạp vào hệ thống.")

        start_total = time.perf_counter()

        # Tự động chuyển đổi nếu đầu vào là định dạng 137 điểm (411 đặc trưng)
        if isinstance(keypoints, np.ndarray) and keypoints.ndim == 2 and keypoints.shape[1] == 411:
            from src.data.vsl_gh_dataset import convert_137_to_67
            keypoints = convert_137_to_67(keypoints, mode="semantic")

        # Bước 1: Nhận diện cử chỉ liên tục bằng CSLR
        cslr_res = self.cslr.predict(keypoints, joint_mask=joint_mask)
        pred_glosses = cslr_res["gloss_list"]

        # Bước 2: Dịch chuỗi cử chỉ sang câu văn tự nhiên bằng ViT5
        if pred_glosses:
            trans_res = self.translate_glosses(pred_glosses, attach_lexicon=attach_lexicon)
            translation = trans_res["translation"]
            lexicon_matches = trans_res.get("lexicon_matches", {})
            vit5_latency = trans_res["latency_ms"]
        else:
            translation = ""
            lexicon_matches = {}
            vit5_latency = 0.0

        total_latency = (time.perf_counter() - start_total) * 1000.0

        return {
            "num_frames": cslr_res["num_frames"],
            "predicted_gloss_list": pred_glosses,
            "predicted_gloss_str": cslr_res["gloss_str"],
            "translation": translation,
            "cslr_latency_ms": cslr_res["latency_ms"],
            "vit5_latency_ms": vit5_latency,
            "total_latency_ms": round(total_latency, 2),
            "lexicon_matches": lexicon_matches,
        }

    def translate_video(
        self,
        video_path: Union[str, Path],
        attach_lexicon: bool = True,
    ) -> Dict[str, Any]:
        """
        Dịch trực tiếp một tệp video cử chỉ liên tục sang câu tiếng Việt tự nhiên.
        Luồng: Video .mp4 -> MediaPipe Holistic trích xuất 67 khớp -> CSLR -> ViT5.
        """
        video_p = Path(video_path)
        if not video_p.exists():
            raise FileNotFoundError(f"Không tìm thấy tệp video tại: {video_p}")

        start_extract = time.perf_counter()
        from src.data.landmark_extractor import CleanHolisticExtractor

        extractor = CleanHolisticExtractor(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1,
        )
        extracted = extractor.extract_from_video(str(video_p))
        extract_latency = (time.perf_counter() - start_extract) * 1000.0

        kps = extracted["keypoints"]  # [T, 67, 3]
        masks = extracted.get("visibility_mask", None)

        res = self.translate_keypoints(kps, joint_mask=masks, attach_lexicon=attach_lexicon)
        res["video_file"] = str(video_p)
        res["extract_latency_ms"] = round(extract_latency, 2)
        res["total_pipeline_ms"] = round(res["total_latency_ms"] + extract_latency, 2)

        return res

    def lookup_lexicon(
        self,
        query: str,
        region: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Tra cứu ký hiệu mẫu từ kho từ điển 8 phương ngữ."""
        if not self.lexicon:
            return []
        return self.lexicon.search(query=query, region=region, category=category, limit=20)

    def get_info(self) -> Dict[str, Any]:
        """Thông tin trạng thái toàn bộ Pipeline Lõi."""
        info = {
            "device": self.device,
            "init_duration_s": round(self.init_duration_s, 2),
            "translator": self.translator.get_info(),
            "cslr_enabled": self.cslr is not None,
            "lexicon_enabled": self.lexicon is not None,
        }
        if self.cslr:
            info["cslr"] = self.cslr.get_info()
        if self.lexicon:
            info["lexicon_entries"] = self.lexicon.total_entries
            info["lexicon_regions"] = self.lexicon.get_regions()
        return info
