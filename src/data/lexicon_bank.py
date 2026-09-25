"""
VSL Lexicon Bank (Từ điển Ký hiệu Đối chiếu & Tra cứu VSL).

Quản lý và tra cứu kho từ vựng ký hiệu đơn lẻ thu thập từ tudienngonngukyhieu.com (HCMUE).
Tính năng:
- Tra cứu video ký hiệu theo từ tiếng Việt (chuẩn hóa không dấu / có dấu).
- Lọc theo phương ngữ (Hà Nội, Bình Dương, TP.HCM, Lâm Đồng, Huế, Cần Thơ, Hải Phòng, Toàn Quốc).
- Lọc theo chủ đề ngữ nghĩa (Gia đình, Giao thông, Tin học, Nghề may, v.v.).
- Đối chiếu độ bao phủ từ vựng với mô hình dịch ViT5 và tập câu VSL-GH.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_METADATA_PATH = PROJECT_ROOT / "data" / "raw_tudienngonngukyhieu" / "metadata.jsonl"
DEFAULT_VIDEOS_DIR = PROJECT_ROOT / "data" / "raw_tudienngonngukyhieu" / "videos"


def remove_vietnamese_tones(text: str) -> str:
    """Normalize Vietnamese text by stripping tones for fuzzy matching."""
    text = text.lower()
    text = re.sub(r"[àáạảãâầấậẩẫăằắặẳẵ]", "a", text)
    text = re.sub(r"[èéẹẻẽêềếệểễ]", "e", text)
    text = re.sub(r"[ìíịỉĩ]", "i", text)
    text = re.sub(r"[òóọỏõôồốộổỗơờớợởỡ]", "o", text)
    text = re.sub(r"[ùúụủũưừứựửữ]", "u", text)
    text = re.sub(r"[ỳýỵỷỹ]", "y", text)
    text = re.sub(r"[đ]", "d", text)
    return text.strip()


class VSLLexiconBank:
    """In-memory searchable index for VSL dictionary items."""

    def __init__(
        self,
        metadata_path: Path = DEFAULT_METADATA_PATH,
        videos_dir: Path = DEFAULT_VIDEOS_DIR,
    ):
        self.metadata_path = Path(metadata_path)
        self.videos_dir = Path(videos_dir)
        self.entries: List[Dict[str, Any]] = []
        self._by_exact_gloss: Dict[str, List[Dict[str, Any]]] = {}
        self._by_normalized_gloss: Dict[str, List[Dict[str, Any]]] = {}
        self._load()

    def _load(self):
        self.entries.clear()
        self._by_exact_gloss.clear()
        self._by_normalized_gloss.clear()

        if not self.metadata_path.exists():
            return

        with open(self.metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    v_name = item.get("video_filename", "")
                    v_path = self.videos_dir / v_name
                    item["exists_on_disk"] = v_path.exists()
                    item["file_path"] = str(v_path) if v_path.exists() else None

                    self.entries.append(item)

                    gloss_lower = item.get("gloss", "").strip().lower()
                    self._by_exact_gloss.setdefault(gloss_lower, []).append(item)

                    norm = remove_vietnamese_tones(gloss_lower)
                    self._by_normalized_gloss.setdefault(norm, []).append(item)
                except Exception:
                    continue

    @property
    def total_entries(self) -> int:
        return len(self.entries)

    @property
    def unique_glosses(self) -> List[str]:
        return sorted(list(self._by_exact_gloss.keys()))

    def get_regions(self) -> List[str]:
        """Return sorted list of unique regions."""
        regions = {e.get("region", "").strip() for e in self.entries if e.get("region", "").strip()}
        return sorted(list(regions))

    def get_categories(self) -> List[str]:
        """Return sorted list of unique categories."""
        cats = {e.get("category", "").strip() for e in self.entries if e.get("category", "").strip()}
        return sorted(list(cats))

    def get_by_gloss(self, gloss: str, exact: bool = True) -> List[Dict[str, Any]]:
        """Look up signs matching a specific gloss."""
        key = gloss.strip().lower()
        if exact:
            return self._by_exact_gloss.get(key, [])
        norm = remove_vietnamese_tones(key)
        return self._by_normalized_gloss.get(norm, [])

    def search(
        self,
        query: str = "",
        region: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Filter entries by query, region dialect, and semantic category."""
        results = self.entries

        if region and region.strip() and region.lower() != "all":
            reg_lower = region.strip().lower()
            results = [e for e in results if reg_lower in e.get("region", "").lower()]

        if category and category.strip() and category.lower() != "all":
            cat_lower = category.strip().lower()
            results = [e for e in results if cat_lower in e.get("category", "").lower()]

        if query and query.strip():
            q_norm = remove_vietnamese_tones(query)
            filtered = []
            for e in results:
                g_norm = remove_vietnamese_tones(e.get("gloss", ""))
                if q_norm in g_norm:
                    filtered.append(e)
            results = filtered

        return results[:limit]

    def get_vocab_overlap(self, target_vocab: List[str]) -> Dict[str, Any]:
        """Compute lexical overlap with another vocabulary list."""
        our_vocab = set(self._by_exact_gloss.keys())
        target_set = {t.strip().lower() for t in target_vocab}
        intersection = our_vocab.intersection(target_set)

        return {
            "total_lexicon_glosses": len(our_vocab),
            "target_vocab_size": len(target_set),
            "overlap_count": len(intersection),
            "overlap_percentage": round(len(intersection) / max(1, len(target_set)) * 100, 2),
            "matched_glosses": sorted(list(intersection)),
        }
