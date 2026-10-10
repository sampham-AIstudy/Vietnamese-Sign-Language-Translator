"""
Plan 15 lần sửa 13 §4 / §9 (step K1): `src/inference/level1_unikey.fusion_target` — Telex/Unikey letter fusion.

AC-K1 (fusion_target half): every row of the reference table §4.3, written out LITERALLY below (independent of the code).
  The Level1Speller half of AC-K1 (on_result and on_label give the same tokens + text) needs the wiring of step K2;
  only the `unikey_mode=False` row is checked through Level1Speller here (its behaviour is the M0 one).
AC-K5: 200 random prediction sequences (fixed seed, 34 classes + SPACE): after every step text == compose(tokens)["text"]
  and a fusion does not change the number of tone tokens (nor any other token than the fused letter).
Pure logic on controlled inputs; no data or checkpoint needed.
"""
import os
import random
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference import level1_segmenter  # noqa: E402
from src.inference.fingerspelling_compose import LETTERS, SPACE, TONE_MARKS, compose, token_kind  # noqa: E402
from src.inference.level1_core import Level1Speller  # noqa: E402
from src.inference.level1_segmenter import LabelEmit  # noqa: E402
from src.inference.level1_unikey import fusion_target  # noqa: E402

# ---------------------------------------------------------------------------------------------------------------------
# §4.3 reference table, LITERAL: (tokens before, predictions in order, tokens after | None, text | None).
# None = the row of §4.3 does not state it (only the stated part is checked).
# ---------------------------------------------------------------------------------------------------------------------
ORACLE_15_PAIRS = [  # the 15 pairs of F2 on the syllable [b, <base>] (d: [d], "[đ,i] không áp")
    (["b", "a"], ["â"], ["b", "â"], "bâ"),        # "baa"
    (["b", "a"], ["ô"], ["b", "â"], "bâ"),
    (["b", "a"], ["ê"], ["b", "â"], "bâ"),
    (["b", "a"], ["ă"], ["b", "ă"], "bă"),        # "baw"
    (["b", "o"], ["â"], ["b", "ô"], "bô"),        # "boo"
    (["b", "o"], ["ô"], ["b", "ô"], "bô"),
    (["b", "o"], ["ê"], ["b", "ô"], "bô"),
    (["b", "o"], ["ơ"], ["b", "ơ"], "bơ"),        # "bow"
    (["b", "o"], ["ư"], ["b", "ơ"], "bơ"),        # "bow"
    (["b", "e"], ["â"], ["b", "ê"], "bê"),        # "bee"
    (["b", "e"], ["ô"], ["b", "ê"], "bê"),
    (["b", "e"], ["ê"], ["b", "ê"], "bê"),
    (["b", "u"], ["ư"], ["b", "ư"], "bư"),        # "buw"
    (["b", "u"], ["ơ"], ["b", "u", "ơ"], "buơ"),  # NGOẠI LỆ F3 (initial consonant)
    (["d"], ["đ"], ["đ"], "đ"),                  # "dd"
    (["đ", "i"], ["đ"], ["đ", "i", "đ"], None),   # "[đ,i] không áp"
]
ORACLE_SPELLING = [
    (["t", "h", "u"], ["ơ", "dấu hỏi"], None, "thuở"),
    (["q", "u"], ["ơ"], None, "quơ"),
    (["h", "u"], ["ơ"], None, "huơ"),
    (["k", "h", "u"], ["ơ"], None, "khuơ"),
    (["u"], ["ơ"], ["ư"], "ư"),
    (["u"], ["ơ", "ơ"], None, "ươ"),
    (["n", "g", "ư"], ["ơ"], None, "ngươ"),
    (["q", "u"], ["â"], None, "quâ"),
    (["g", "i", "a"], ["â"], None, "giâ"),
    (["g", "i"], ["ê"], None, "giê"),
    (["b", "a", "dấu sắc"], ["â"], ["b", "â", "dấu sắc"], "bấ"),  # F1
    (["b", "a", " "], ["â"], ["b", "a", " ", "â"], None),          # not across a SPACE
    ([], ["â"], ["â"], None),
]
# unikey_mode=False: [b,a]+â -> [b,a,â] (Level1Speller only: fusion_target has no mode)
ORACLE_UNIKEY_OFF = (["b", "a"], ["â"], ["b", "a", "â"])

# the 15 pairs of §4.1 (fact of the table, written out literally)
TABLE_15 = {
    "a": {"â": "â", "ô": "â", "ê": "â", "ă": "ă"},
    "o": {"â": "ô", "ô": "ô", "ê": "ô", "ơ": "ơ", "ư": "ơ"},
    "e": {"â": "ê", "ô": "ê", "ê": "ê"},
    "u": {"ơ": "ư", "ư": "ư"},
    "d": {"đ": "đ"},
}


def apply_predictions(tokens, predictions):
    """Apply each prediction: fused at fusion_target's index, otherwise appended (the K2 contract of the caller)."""
    toks = list(tokens)
    for p in predictions:
        hit = fusion_target(toks, p)
        if hit is None:
            toks.append(p)
        else:
            idx, target, _rule = hit
            toks[idx] = target
    return toks


class TestFusionOracleK1(unittest.TestCase):
    """AC-K1, fusion_target half: every row of §4.3."""

    def _check_rows(self, rows):
        for before, preds, after, text in rows:
            with self.subTest(before=before, preds=preds):
                toks = apply_predictions(before, preds)
                if after is not None:
                    self.assertEqual(toks, after)
                if text is not None:
                    self.assertEqual(compose(toks)["text"], text)

    def test_15_pairs(self):
        self._check_rows(ORACLE_15_PAIRS)

    def test_spelling_rows(self):
        self._check_rows(ORACLE_SPELLING)

    def test_single_step_return_values(self):
        # the (index, target, rule) of the one-prediction rows of §4.3
        self.assertEqual(fusion_target(["b", "a"], "ô"), (1, "â", "a+ô"))
        self.assertEqual(fusion_target(["b", "o"], "ư"), (1, "ơ", "o+ư"))
        self.assertEqual(fusion_target(["b", "e"], "ô"), (1, "ê", "e+ô"))
        self.assertEqual(fusion_target(["b", "u"], "ư"), (1, "ư", "u+ư"))
        self.assertEqual(fusion_target(["d"], "đ"), (0, "đ", "d+đ"))
        self.assertEqual(fusion_target(["u"], "ơ"), (0, "ư", "u+ơ"))
        self.assertEqual(fusion_target(["g", "i", "a"], "â"), (2, "â", "a+â"))
        self.assertEqual(fusion_target(["b", "a", "dấu sắc"], "â"), (1, "â", "a+â"))
        for tokens, pred in ((["b", "u"], "ơ"), (["t", "h", "u"], "ơ"), (["q", "u"], "ơ"), (["h", "u"], "ơ"),
                             (["k", "h", "u"], "ơ"), (["n", "g", "ư"], "ơ"), (["q", "u"], "â"), (["g", "i"], "ê"),
                             (["b", "a", " "], "â"), ([], "â"), (["đ", "i"], "đ")):
            with self.subTest(tokens=tokens, pred=pred):
                self.assertIsNone(fusion_target(tokens, pred))

    def test_unikey_off_row_through_speller(self):
        before, preds, after = ORACLE_UNIKEY_OFF
        sp = Level1Speller(0.5, unikey_mode=False)
        sp.tokens = list(before)
        for i, p in enumerate(preds):
            sp.on_result(i, {"status": "ok", "prediction": p, "confidence": 0.9}, float(i))
        self.assertEqual(sp.tokens, after)
        sp = Level1Speller(0.5, unikey_mode=False)
        sp.tokens = list(before)
        for i, p in enumerate(preds):
            sp.on_label(i, LabelEmit(seq=i, ts_ms=float(i), prediction=p, confidence=0.9, action="append",
                                     run_since_ms=0.0, result={"status": "ok", "prediction": p, "confidence": 0.9}))
        self.assertEqual(sp.tokens, after)


class TestFusionRulesK1(unittest.TestCase):
    """Consequences of F1-F6 stated in §4.2 (beyond the literal rows)."""

    def test_one_table_15_pairs(self):
        from src.inference import level1_unikey
        self.assertIs(level1_unikey.DIACRITIC_FUSION, level1_segmenter.DIACRITIC_FUSION)
        self.assertEqual(level1_segmenter.DIACRITIC_FUSION, TABLE_15)
        self.assertEqual(sum(len(v) for v in TABLE_15.values()), 15)

    def test_every_pair_on_b_syllable_except_u_horn(self):
        # F2 on [b, <base>] for every pair of the table; F3: (u, ơ) after an initial consonant is not fused
        for base, triggers in TABLE_15.items():
            for pred, target in triggers.items():
                with self.subTest(base=base, pred=pred):
                    got = fusion_target(["b", base], pred)
                    if (base, pred) == ("u", "ơ"):
                        self.assertIsNone(got)
                    else:
                        self.assertEqual(got, (1, target, f"{base}+{pred}"))

    def test_f1_tone_marks_after_the_last_letter(self):
        self.assertEqual(fusion_target(["b", "o", "dấu huyền"], "ô"), (1, "ô", "o+ô"))
        self.assertEqual(fusion_target(["b", "e", "dấu sắc", "dấu nặng"], "ê"), (1, "ê", "e+ê"))
        self.assertEqual(fusion_target(["u", "dấu sắc"], "ơ"), (0, "ư", "u+ơ"))  # F3: u still opens the syllable
        # a syllable with only tone marks after the SPACE has no letter
        self.assertIsNone(fusion_target(["b", "a", SPACE, "dấu sắc"], "â"))
        # the last letter is not a key: no search further back
        self.assertIsNone(fusion_target(["b", "a", "n"], "â"))
        self.assertIsNone(fusion_target(["b", "a", "n", "dấu sắc"], "â"))

    def test_f3_initial_consonant_only_in_the_same_syllable(self):
        self.assertEqual(fusion_target(["x", SPACE, "u"], "ơ"), (2, "ư", "u+ơ"))
        self.assertIsNone(fusion_target(["x", SPACE, "t", "u"], "ơ"))
        self.assertEqual(fusion_target(["t", "h", "u"], "ư"), (2, "ư", "u+ư"))  # (u, ư) always fused
        self.assertEqual(fusion_target(["q", "u"], "ư"), (1, "ư", "u+ư"))

    def test_predictions_outside_the_table(self):
        for pred in list(TONE_MARKS) + [SPACE, None, "b", "i", "a", "o", "u", "d"]:
            for tokens in (["b", "a"], ["b", "o"], ["u"], ["d"], ["b", "e", "dấu sắc"]):
                with self.subTest(tokens=tokens, pred=pred):
                    self.assertIsNone(fusion_target(tokens, pred))

    def test_pure_and_sequence_input(self):
        toks = ["b", "a", "dấu sắc"]
        self.assertEqual(fusion_target(toks, "â"), (1, "â", "a+â"))
        self.assertEqual(toks, ["b", "a", "dấu sắc"])
        self.assertEqual(fusion_target(("b", "a"), "ă"), (1, "ă", "a+ă"))

    def test_unknown_token_raises(self):
        with self.assertRaises(ValueError):
            fusion_target(["b", "?"], "â")

    def test_module_passes_the_source_guard_rules(self):
        # DoD 7 guard rules on the new file (it enters the plan 15 closure with step K2)
        from tests.test_backend_source_guard import ALL_RULES, _read, scan_source
        rel = "src/inference/level1_unikey.py"
        findings = scan_source(_read(os.path.join(PROJECT_ROOT, rel)), rel, ALL_RULES)
        self.assertEqual(findings, [], "\n".join(f"{f.path}:{f.line} {f.rule} {f.snippet}" for f in findings))


class TestFusionRandomK5(unittest.TestCase):
    """AC-K5: 200 random prediction sequences, fixed seed, 34 classes + SPACE."""

    SEED = 20261008
    N_SEQUENCES = 200
    MAX_LEN = 40

    def test_random_sequences_keep_text_and_tones(self):
        vocab = list(LETTERS) + list(TONE_MARKS)
        self.assertEqual(len(vocab), 34)
        vocab.append(SPACE)
        rng = random.Random(self.SEED)
        n_fused = n_kept_f3 = 0
        for n in range(self.N_SEQUENCES):
            toks = []
            for _ in range(rng.randint(1, self.MAX_LEN)):
                p = rng.choice(vocab)
                before = list(toks)
                hit = fusion_target(toks, p)
                self.assertEqual(toks, before)  # pure
                if p == "ơ" and len(before) >= 2 and before[-1] == "u" and token_kind(before[-2]) == "letter":
                    self.assertIsNone(hit, (n, before))  # F3: u after an initial consonant keeps the "ơ"
                    n_kept_f3 += 1
                if hit is None:
                    toks.append(p)
                else:
                    idx, target, rule = hit
                    n_fused += 1
                    base = before[idx]
                    self.assertEqual(token_kind(base), "letter")
                    self.assertEqual(token_kind(target), "letter")
                    self.assertEqual(rule, f"{base}+{p}")
                    self.assertEqual(TABLE_15[base][p], target)
                    self.assertTrue(all(token_kind(t) == "tone" for t in before[idx + 1:]), (n, before, p))
                    toks[idx] = target
                    # F6: one letter replaced, nothing else moved, same number of tone tokens
                    self.assertEqual(len(toks), len(before))
                    self.assertEqual(toks[:idx] + toks[idx + 1:], before[:idx] + before[idx + 1:])
                    self.assertEqual(sum(token_kind(t) == "tone" for t in toks),
                                     sum(token_kind(t) == "tone" for t in before))
                    # only the active syllable (after the last SPACE) changes in the text
                    if SPACE in before:
                        self.assertEqual(compose(toks)["text"].rsplit(SPACE, 1)[0],
                                         compose(before)["text"].rsplit(SPACE, 1)[0])
                text = compose(toks)["text"]
                self.assertEqual(text, compose(list(toks))["text"])
                self.assertIsInstance(text, str)
        self.assertGreater(n_fused, 0)
        self.assertGreater(n_kept_f3, 0)


if __name__ == "__main__":
    unittest.main()
