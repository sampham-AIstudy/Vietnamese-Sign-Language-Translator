"""
Core text box logic for Level 1 (web/desktop shared).
"""
from typing import Dict, Optional, Sequence

from src.inference.fingerspelling_compose import SPACE, compose, token_kind


def textbox_view(tokens: Sequence[str], rejected: Optional[Dict] = None) -> Dict:
    """
    Computes the view state for the textbox based on the current sequence of tokens.
    """
    # Verify all current tokens so ValueError is raised for invalid ones
    for tok in tokens:
        token_kind(tok)

    # 1. Find the start of the active syllable (after the last SPACE)
    k = 0
    for i in range(len(tokens) - 1, -1, -1):
        if tokens[i] == SPACE:
            k = i + 1
            break

    active_tokens = list(tokens[k:])
    
    # 2. Compute committed, active, and text
    committed = compose(tokens[:k])["text"]
    active_comp = compose(active_tokens)
    active = active_comp["text"]
    full_comp = compose(tokens)
    text = full_comp["text"]
    
    # Invariant: committed + active == text
    
    # 3. Cursor
    cursor = len(text)
    
    # 4. active_tone and tone_changes
    active_tone = None
    tones_in_active = []
    for tok in active_tokens:
        if token_kind(tok) == "tone":
            active_tone = tok
            tones_in_active.append(tok)
            
    # "danh sách {from, to} cho các dấu bị thay trong âm tiết đang gõ (từ cảnh báo multiple_tones của compose ứng với chỉ số trong active_tokens)"
    tone_changes = []
    for w in active_comp["warnings"]:
        if w["code"] == "multiple_tones":
            idx = w["token_index"]
            from_tone = active_tokens[idx]
            to_tone = tones_in_active[-1]
            tone_changes.append({"from": from_tone, "to": to_tone})
            
    # 5. warnings
    warnings = [w for w in full_comp["warnings"] if w["code"] == "tone_without_vowel"]
    
    # 6. preview
    preview = None
    if rejected is not None and rejected.get("prediction") is not None:
        pred = rejected["prediction"]
        conf = rejected.get("confidence")
        
        # Verify the rejected prediction is a valid token kind
        token_kind(pred)
        
        active_if = "" if pred == SPACE else compose(active_tokens + [pred])["text"]
        preview = {
            "token": pred,
            "confidence": conf,
            "active_if_accepted": active_if
        }
        
    return {
        "committed": committed,
        "active": active,
        "text": text,
        "cursor": cursor,
        "active_tokens": active_tokens,
        "active_tone": active_tone,
        "tone_changes": tone_changes,
        "warnings": warnings,
        "preview": preview,
    }
