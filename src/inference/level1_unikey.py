"""
Level 1 "gõ kiểu Unikey" (plan 15 lần sửa 13 §4.2): which token a model prediction replaces in the active syllable.

Pure module (no torch / cv2 / GUI). One function, `fusion_target(tokens, prediction)`, decides whether the prediction is
FUSED into a letter already typed (Telex style "aa" -> "â") instead of being appended. It never changes the tokens.

Rules (the letter-replacement rule is fixed in advance; there is no new tone rule):
F1 Base position: the LAST letter of the syllable being typed (the tokens after the last SPACE); after it only tone mark
   tokens may stand (Telex "asa" -> "ấ"). A syllable without a letter, a last letter that is not a key of the table, or a
   prediction that is not in the table of that letter -> no fusion (None: the caller appends the token as before).
F2 Table = the 15 pairs of `DIACRITIC_FUSION` (the ONE copy, `src/inference/level1_segmenter.py`), not extended here.
   Telex: a+{â,ô,ê} = "aa"->â; a+ă = "aw"->ă; o+{â,ô,ê} = "oo"->ô; o+{ơ,ư} = "ow"->ơ; e+{â,ô,ê} = "ee"->ê;
   u+{ơ,ư} = "uw"->ư; d+đ = "dd"->đ.
F3 Exception "uơ" (spelling: thuở, quơ, huơ, khuơ): (u, ơ) is fused ONLY when that `u` is the FIRST letter of the
   syllable (no initial consonant, `q` included); with an initial consonant the prediction "ơ" is kept as it is (DoD 6:
   a valid raw sequence is not rewritten). (u, ư) is always fused. (u, ơ) is the only pair of the table whose raw
   sequence can be valid Vietnamese.
F4 qu/gi follow from F1-F3: [q,u]+â -> "quâ"; [q,u]+ơ -> "quơ"; [g,i,a]+â -> "giâ"; [g,i]+ê -> "giê".
F5 ươ: [..,ư]+ơ -> "ươ" (ư is not a key); [u]+ơ -> "ư" (F3), then +ơ -> "ươ". No "uow" rule (that would change two
   tokens at once = guess a letter the model did not output).
F6 A fusion replaces ONE letter by ONE letter at the returned index: no tone token is created, removed or moved, the
   number of tokens is unchanged; the text stays `compose(tokens)["text"]`.
F7 (trace, plan step K2) the caller logs the replacement with source "fusion", the model prediction and `rule`.
"""
import unicodedata
from typing import Optional, Sequence, Tuple

from src.inference.fingerspelling_compose import token_kind
from src.inference.level1_segmenter import DIACRITIC_FUSION

# F3: (base letter, prediction) fused only when the base letter opens the syllable
SYLLABLE_INITIAL_ONLY = frozenset({("u", "ơ")})


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def fusion_target(tokens: Sequence[str], prediction: Optional[str]) -> Optional[Tuple[int, str, str]]:
    """(index, target, rule) when `prediction` fuses into the letter `tokens[index]` (which becomes `target`), with
    rule = "<base letter>+<prediction>"; None when the prediction is to be appended (rules F1-F5 of the module doc).
    `tokens` are Level 1 tokens (letters, tone marks, SPACE); an unknown token raises ValueError (as compose does).
    Pure: `tokens` is not modified."""
    if not isinstance(prediction, str):
        return None
    pred = _nfc(prediction)
    base_index = None
    for i in range(len(tokens) - 1, -1, -1):          # F1: skip the tone marks typed after the last letter
        kind = token_kind(tokens[i])
        if kind == "tone":
            continue
        if kind == "letter":
            base_index = i
        break                                          # a SPACE (or the letter found) ends the search
    if base_index is None:
        return None
    base = _nfc(tokens[base_index])
    table = DIACRITIC_FUSION.get(base)
    if table is None or pred not in table:
        return None
    if (base, pred) in SYLLABLE_INITIAL_ONLY:          # F3: only when no letter precedes it in the syllable
        for j in range(base_index - 1, -1, -1):
            kind = token_kind(tokens[j])
            if kind == "space":
                break
            if kind == "letter":
                return None
    return base_index, table[pred], f"{base}+{pred}"
