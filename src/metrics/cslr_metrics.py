"""
CSLR Metrics Module: Word Error Rate (WER) and CTC Sequence Decoding

Features:
- CTC Greedy Decoding (argmax, collapse consecutive repeats, strip blank)
- Exact Levenshtein Edit Distance with S (Substitutions), D (Deletions), I (Insertions) decomposition
- Sentence-level and corpus-level WER computation
- CSLRMetricTracker for batch accumulation during validation and evaluation
"""

from typing import List, Dict, Tuple, Any, Optional, Union
import torch
import numpy as np


def ctc_greedy_decode(
    log_probs: torch.Tensor,
    sequence_lengths: Optional[torch.Tensor] = None,
    blank_id: int = 0,
) -> List[List[int]]:
    """
    Decodes CTC log-probabilities using greedy (argmax) best-path decoding.
    
    Algorithm:
      1. Per frame: token = argmax_c(log_probs[t, b, c])
      2. Consecutive identical tokens collapsed: [A, A, B] -> [A, B]
      3. Blank tokens (blank_id) removed: [A, blank, B] -> [A, B]
    
    Args:
        log_probs: Tensor of shape [T, B, C] or [B, T, C].
        sequence_lengths: Optional Tensor of shape [B] indicating valid frame counts.
                          If None, full length T is assumed for all batches.
        blank_id: Index of the CTC blank token (default: 0).
        
    Returns:
        List of decoded token ID lists: length B, each inner list containing predicted token IDs.
    """
    if log_probs.dim() != 3:
        raise ValueError(f"Expected 3D log_probs tensor [T, B, C] or [B, T, C], got {log_probs.dim()}D.")

    # Determine dimension ordering
    # Convention: if shape[0] > shape[1], or standard PyTorch CTCLoss format [T, B, C]
    # We standardize to [B, T, C]
    if log_probs.size(0) != sequence_lengths.size(0) if sequence_lengths is not None else False:
        # Likely [T, B, C]
        log_probs_btc = log_probs.transpose(0, 1).contiguous()
    else:
        log_probs_btc = log_probs

    batch_size, max_t, num_classes = log_probs_btc.shape
    argmax_tokens = torch.argmax(log_probs_btc, dim=-1).cpu().numpy()  # [B, T]

    if sequence_lengths is not None:
        seq_lens = sequence_lengths.cpu().numpy().astype(int)
    else:
        seq_lens = np.full(batch_size, max_t, dtype=int)

    decoded_batch: List[List[int]] = []

    for b in range(batch_size):
        valid_len = int(seq_lens[b])
        tokens = argmax_tokens[b, :valid_len]

        collapsed: List[int] = []
        prev_tok: Optional[int] = None
        for tok in tokens:
            tok_int = int(tok)
            if tok_int != prev_tok:
                if tok_int != blank_id:
                    collapsed.append(tok_int)
                prev_tok = tok_int

        decoded_batch.append(collapsed)

    return decoded_batch


def tokens_to_words(
    token_seqs: List[List[int]],
    vocab: Union[Dict[int, str], List[str], Any],
) -> List[List[str]]:
    """
    Maps sequences of token IDs to gloss strings using a vocabulary lookup.
    """
    word_seqs: List[List[str]] = []
    for seq in token_seqs:
        words = []
        for t in seq:
            if hasattr(vocab, "id_to_gloss"):
                word = vocab.id_to_gloss.get(t, f"<unk_{t}>")
            elif hasattr(vocab, "idx_to_gloss"):
                word = vocab.idx_to_gloss.get(t, f"<unk_{t}>")
            elif hasattr(vocab, "decode_indices"):
                word = vocab.idx_to_gloss.get(t, f"<unk_{t}>")
            elif isinstance(vocab, dict):
                word = vocab.get(t, f"<unk_{t}>")
            elif isinstance(vocab, (list, tuple)):
                word = vocab[t] if 0 <= t < len(vocab) else f"<unk_{t}>"
            else:
                word = str(t)
            words.append(word)
        word_seqs.append(words)
    return word_seqs


def levenshtein_distance(
    ref: List[Any],
    hyp: List[Any],
) -> Tuple[int, int, int, int]:
    """
    Computes Levenshtein edit distance between reference and hypothesis sequences.
    
    Decomposition:
      Distance = S (Substitutions) + D (Deletions) + I (Insertions)
      where:
        - Substitution: replacing ref word with different hyp word
        - Deletion: ref word missed by hypothesis
        - Insertion: spurious word added by hypothesis
    
    Returns:
      Tuple of (total_distance, S, D, I)
    """
    r_len = len(ref)
    h_len = len(hyp)

    # dp[i][j] = (cost, S, D, I)
    dp: List[List[Tuple[int, int, int, int]]] = [
        [(0, 0, 0, 0) for _ in range(h_len + 1)] for _ in range(r_len + 1)
    ]

    for i in range(1, r_len + 1):
        dp[i][0] = (i, 0, i, 0)  # i deletions
    for j in range(1, h_len + 1):
        dp[0][j] = (j, 0, 0, j)  # j insertions

    for i in range(1, r_len + 1):
        for j in range(1, h_len + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                # 1. Substitution
                cost_sub = dp[i - 1][j - 1][0] + 1
                s_sub = dp[i - 1][j - 1][1] + 1
                d_sub = dp[i - 1][j - 1][2]
                i_sub = dp[i - 1][j - 1][3]
                cand_sub = (cost_sub, s_sub, d_sub, i_sub)

                # 2. Deletion (omitted in hyp)
                cost_del = dp[i - 1][j][0] + 1
                s_del = dp[i - 1][j][1]
                d_del = dp[i - 1][j][2] + 1
                i_del = dp[i - 1][j][3]
                cand_del = (cost_del, s_del, d_del, i_del)

                # 3. Insertion (extra in hyp)
                cost_ins = dp[i][j - 1][0] + 1
                s_ins = dp[i][j - 1][1]
                d_ins = dp[i][j - 1][2]
                i_ins = dp[i][j - 1][3] + 1
                cand_ins = (cost_ins, s_ins, d_ins, i_ins)

                # Standard tie-breaking: prefer substitution over ins/del
                best = min(cand_sub, cand_del, cand_ins, key=lambda x: x[0])
                dp[i][j] = best

    return dp[r_len][h_len]


def compute_wer(
    hypotheses: List[List[Any]],
    references: List[List[Any]],
) -> Dict[str, Union[float, int]]:
    """
    Computes Word Error Rate (WER) across a set of sequence pairs.
    
    Formula:
      WER = (S + D + I) / N_ref * 100%
      where N_ref is total number of words in reference sentences.
      
    Args:
        hypotheses: List of predicted sequences (gloss tokens or strings).
        references: List of ground-truth sequences.
        
    Returns:
        Dict containing:
          - wer: float percentage (e.g. 15.42)
          - substitutions: total S count
          - deletions: total D count
          - insertions: total I count
          - sub_rate: S / N_ref * 100%
          - del_rate: D / N_ref * 100%
          - ins_rate: I / N_ref * 100%
          - total_ref_words: N_ref
          - total_hyp_words: N_hyp
    """
    if len(hypotheses) != len(references):
        raise ValueError(f"Hypotheses count ({len(hypotheses)}) != References count ({len(references)})")

    total_s = 0
    total_d = 0
    total_i = 0
    total_ref_words = 0
    total_hyp_words = 0

    for hyp, ref in zip(hypotheses, references):
        total_ref_words += len(ref)
        total_hyp_words += len(hyp)
        _, s, d, i = levenshtein_distance(ref, hyp)
        total_s += s
        total_d += d
        total_i += i

    total_edits = total_s + total_d + total_i

    if total_ref_words == 0:
        wer = 100.0 if total_hyp_words > 0 else 0.0
        sub_rate = 0.0
        del_rate = 0.0
        ins_rate = 0.0
    else:
        wer = (total_edits / total_ref_words) * 100.0
        sub_rate = (total_s / total_ref_words) * 100.0
        del_rate = (total_d / total_ref_words) * 100.0
        ins_rate = (total_i / total_ref_words) * 100.0

    return {
        "wer": round(wer, 2),
        "substitutions": total_s,
        "deletions": total_d,
        "insertions": total_i,
        "sub_rate": round(sub_rate, 2),
        "del_rate": round(del_rate, 2),
        "ins_rate": round(ins_rate, 2),
        "total_ref_words": total_ref_words,
        "total_hyp_words": total_hyp_words,
    }


class CSLRMetricTracker:
    """
    Accumulates batch CTC losses, hypotheses, and references during evaluation.
    """
    def __init__(self, vocab: Optional[Any] = None, blank_id: int = 0):
        self.vocab = vocab
        self.blank_id = blank_id
        self.reset()

    def reset(self) -> None:
        self.total_loss = 0.0
        self.total_samples = 0
        self.all_hypotheses: List[List[int]] = []
        self.all_references: List[List[int]] = []

    def update(
        self,
        loss: float,
        log_probs: torch.Tensor,
        input_lengths: torch.Tensor,
        target_sequences: List[List[int]],
    ) -> None:
        """
        Updates tracker with a batch evaluation step.
        """
        batch_size = len(target_sequences)
        self.total_loss += float(loss) * batch_size
        self.total_samples += batch_size

        decoded_batch = ctc_greedy_decode(
            log_probs, sequence_lengths=input_lengths, blank_id=self.blank_id
        )
        self.all_hypotheses.extend(decoded_batch)
        self.all_references.extend(target_sequences)

    def compute(self) -> Dict[str, Any]:
        """
        Computes aggregated loss and WER metrics.
        """
        avg_loss = (self.total_loss / self.total_samples) if self.total_samples > 0 else 0.0
        wer_dict = compute_wer(self.all_hypotheses, self.all_references)
        wer_dict["loss"] = round(avg_loss, 4)
        wer_dict["num_samples"] = self.total_samples
        return wer_dict
