"""
Level 1 "Đánh vần": turn a list of accepted tokens (letters, tone marks, spaces) into Vietnamese text.

Pure module (no torch / fastapi). Tokens are the Level 1 class names
(scripts/build_alphabet_tasks.ALPHABET_CLASSES) plus SPACE = " ".

Rules (plan 03 §3.3):
1. A syllable is the run of tokens between two SPACE tokens. Letters are concatenated in order.
   A tone mark applies to the WHOLE syllable wherever it stands in it (usually signed after the
   last letter, like Telex).
2. Two or more tone marks in one syllable: the LAST one is used; each earlier one gets a
   `multiple_tones` warning.
3. A syllable without a vowel: no tone is applied, letters are kept unchanged, and the tone mark
   gets a `tone_without_vowel` warning. Letters are never corrected or guessed.
4. Vowel that carries the tone. Vowels: a ă â e ê i o ô ơ u ư y. The "u" of a syllable-initial "qu"
   is skipped; the "i" of a syllable-initial "gi" is skipped when another vowel follows it (when
   skipping would leave no vowel, nothing is skipped). On the remaining vowel cluster (the first
   contiguous run of candidate vowels):
   (a) it has a vowel with a diacritic (ă â ê ô ơ ư): the LAST such vowel ("ươ" -> ơ);
   (b) else, when a final consonant follows the cluster: the last vowel of the cluster;
   (c) else, 3 vowels: the middle one;
   (d) else, 2 vowels: the FIRST one (traditional style: hòa, thủy);
   (e) 1 vowel: that vowel.
   TONE_STYLE = "traditional" names this choice.
5. Output is NFC, lower case; no capitalisation, spaces are kept exactly as given.
"""
import unicodedata
from typing import Any, Dict, List, Sequence

LETTERS = ("a", "ă", "â", "b", "c", "d", "đ", "e", "ê", "g", "h", "i", "k", "l", "m", "n", "o", "ô", "ơ",
           "p", "q", "r", "s", "t", "u", "ư", "v", "x", "y")
TONE_MARKS = {  # class name -> combining mark
    "dấu sắc": "\u0301",
    "dấu huyền": "\u0300",
    "dấu hỏi": "\u0309",
    "dấu ngã": "\u0303",
    "dấu nặng": "\u0323",
}
SPACE = " "
TONE_STYLE = "traditional"
VOWELS = frozenset("aăâeêioôơuưy")
MARKED_VOWELS = frozenset("ăâêôơư")
_LETTER_SET = frozenset(LETTERS)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def short_repr(value: Any, limit: int = 40) -> str:
    """repr(value) cut to its first `limit` characters + "…", so error messages that quote client
    input stay short (a 500 KB token must not be echoed back)."""
    r = repr(value)
    return r if len(r) <= limit else r[:limit] + "…"


def token_kind(token: Any) -> str:
    """'letter' | 'tone' | 'space'. Raises ValueError for anything else."""
    if isinstance(token, str):
        if token == SPACE:
            return "space"
        t = _nfc(token)
        if t in _LETTER_SET:
            return "letter"
        if t in TONE_MARKS:
            return "tone"
    raise ValueError(f"unknown token {short_repr(token)}")


def tone_vowel_index(letters: Sequence[str]) -> int:
    """Index in `letters` of the vowel that carries the tone, or -1 when there is no vowel."""
    candidates = [i for i, c in enumerate(letters) if c in VOWELS]
    skip = set()
    if len(letters) >= 2 and letters[0] == "q" and letters[1] == "u":
        skip.add(1)
    if len(letters) >= 2 and letters[0] == "g" and letters[1] == "i" and any(c in VOWELS for c in letters[2:]):
        skip.add(1)
    if [i for i in candidates if i not in skip]:
        candidates = [i for i in candidates if i not in skip]
    if not candidates:
        return -1
    cluster = [candidates[0]]
    for i in candidates[1:]:
        if i != cluster[-1] + 1:
            break
        cluster.append(i)
    marked = [i for i in cluster if letters[i] in MARKED_VOWELS]
    if marked:
        return marked[-1]
    if cluster[-1] < len(letters) - 1:  # a final consonant follows the cluster
        return cluster[-1]
    if len(cluster) == 3:
        return cluster[1]
    return cluster[0]


def _compose_syllable(items: List[tuple], warnings: List[Dict[str, Any]]) -> str:
    """items: [(token_index, kind, nfc_token)] of one syllable (no spaces)."""
    letters = [t for _, k, t in items if k == "letter"]
    tones = [(i, t) for i, k, t in items if k == "tone"]
    if not tones:
        return "".join(letters)
    for i, t in tones[:-1]:
        warnings.append({"code": "multiple_tones", "token_index": i,
                         "message": f"tokens[{i}] '{t}' ignored: the syllable has a later tone mark "
                                    f"(tokens[{tones[-1][0]}] '{tones[-1][1]}')"})
    tone_index, tone = tones[-1]
    v = tone_vowel_index(letters)
    if v < 0:
        warnings.append({"code": "tone_without_vowel", "token_index": tone_index,
                         "message": f"tokens[{tone_index}] '{tone}' not applied: the syllable has no vowel"})
        return "".join(letters)
    letters = list(letters)
    letters[v] = _nfc(letters[v] + TONE_MARKS[tone])
    return "".join(letters)


def compose(tokens: Sequence[str]) -> Dict[str, Any]:
    """tokens -> {"text": NFC str, "syllables": [non-empty syllables], "warnings": [{code, token_index, message}]}.
    Raises ValueError (naming the position) for an unknown token."""
    kinds = []
    for i, tok in enumerate(tokens):
        try:
            kinds.append(token_kind(tok))
        except ValueError:
            raise ValueError(f"tokens[{i}]: unknown token {short_repr(tok)}") from None
    warnings: List[Dict[str, Any]] = []
    parts: List[str] = []
    syllables: List[str] = []
    current: List[tuple] = []

    def flush():
        if current:
            s = _compose_syllable(current, warnings)
            parts.append(s)
            if s:
                syllables.append(s)
            current.clear()

    for i, (tok, kind) in enumerate(zip(tokens, kinds)):
        if kind == "space":
            flush()
            parts.append(SPACE)
        else:
            current.append((i, kind, _nfc(tok)))
    flush()
    return {"text": _nfc("".join(parts)), "syllables": syllables, "warnings": warnings}
