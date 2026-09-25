"""
Canonical Translation Text Normalizer
Provides safe, deterministic transformations between:
1. CSLR/VSL-GH predicted gloss sequences (ALL-CAPS, hyphenated compounds, list of strings)
2. Normalized VSL source text for seq2seq translation models
3. Target Vietnamese text normalization (punctuation, casing, Unicode NFC)

Rules:
- Strictly deterministic transformations (Unicode NFC, casing, separator collapse, whitespace)
- No heuristic synonyms or lossy manual rewrites
"""

import re
import unicodedata
from typing import List, Union, Optional, Tuple


def normalize_unicode(text: str) -> str:
    """Normalizes text to Unicode NFC precomposed format."""
    if not text:
        return ""
    return unicodedata.normalize("NFC", text)


def normalize_vsl_source(
    vsl_input: Union[str, List[str]],
    casing: str = "lower",
    strip_hyphens: bool = True,
    strip_punctuation: bool = True,
) -> str:
    """
    Normalizes VSL gloss or text sequences for consumption by the translation model.

    Transformations:
      1. Converts List[str] of glosses to string.
      2. Unicode NFC normalization.
      3. Replaces compound separators ('-', '_') with space if strip_hyphens is True.
      4. Strips extraneous punctuation if strip_punctuation is True.
      5. Normalizes whitespace (single space between tokens).
      6. Applies deterministic casing ('lower', 'upper', or 'preserve').

    Examples:
      ["TÔI", "ĐĂNG-KÝ", "KHÁM", "SỨC-KHỎE", "MUỐN"] -> "tôi đăng ký khám sức khỏe muốn"
      "Tôi tuổi 19 ." -> "tôi tuổi 19"
    """
    if isinstance(vsl_input, (list, tuple)):
        # Join tokens with space
        raw_text = " ".join(str(tok).strip() for tok in vsl_input if str(tok).strip())
    else:
        raw_text = str(vsl_input)

    text = normalize_unicode(raw_text)

    # 1. Separator normalization
    if strip_hyphens:
        text = text.replace("-", " ").replace("_", " ")

    # 2. Punctuation normalization
    if strip_punctuation:
        text = re.sub(r"[.,!?;:\"\'()\[\]{}]", " ", text)

    # 3. Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # 4. Casing
    if casing == "lower":
        text = text.lower()
    elif casing == "upper":
        text = text.upper()
    elif casing == "sentence":
        if text:
            text = text[0].upper() + text[1:].lower()

    return text


def normalize_vietnamese_target(
    vi_text: str,
    standardize_punct_spacing: bool = True,
) -> str:
    """
    Normalizes natural Vietnamese target text for evaluation and training.

    Transformations:
      1. Unicode NFC normalization.
      2. Standardize quote characters.
      3. Collapse whitespace.
      4. Punctuation spacing: removes spaces before punctuation marks (e.g. ' .' -> '.').
    """
    text = normalize_unicode(vi_text)

    # Standardize quotes
    text = re.sub(r"[\u2018\u2019\u201A\u201B]", "'", text)
    text = re.sub(r"[\u201C\u201D\u201E\u201F]", '"', text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    if standardize_punct_spacing:
        # Remove spaces before punctuation (common in tokenized corpus: "tôi đi học ." -> "tôi đi học.")
        text = re.sub(r"\s+([.,!?;:])", r"\1", text)
        # Ensure single space after punctuation if followed by a letter/number
        text = re.sub(r"([.,!?;:])(?=[A-Za-zÀ-ỹ0-9])", r"\1 ", text)

    return text


class CanonicalTranslationNormalizer:
    """
    Stateful helper combining source and target normalization pipelines.
    """
    def __init__(self, casing: str = "lower"):
        self.casing = casing

    def normalize_source(self, vsl: Union[str, List[str]]) -> str:
        return normalize_vsl_source(vsl, casing=self.casing)

    def normalize_target(self, vi: str) -> str:
        return normalize_vietnamese_target(vi)

    def normalize_pair(self, vsl: Union[str, List[str]], vi: str) -> Tuple[str, str]:
        return self.normalize_source(vsl), self.normalize_target(vi)
