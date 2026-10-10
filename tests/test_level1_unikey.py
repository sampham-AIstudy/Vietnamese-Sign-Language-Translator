"""
Plan 15 lần sửa 13 §4 / §9 (step K1): `src/inference/level1_unikey.fusion_target` — Telex/Unikey letter fusion.

AC-K1 (fusion_target half): every row of the reference table §4.3, written out LITERALLY below (independent of the code).
  The Level1Speller half of AC-K1 (on_result and on_label give the same tokens + text) needs the wiring of step K2;
  only the `unikey_mode=False` row is checked through Level1Speller here (its behaviour is the M0 one).
AC-K5: 200 random prediction sequences (fixed seed, 34 classes + SPACE): after every step text == compose(tokens)["text"]
  and a fusion does not change the number of tone tokens (nor any other token than the fused letter).
Step K2 (same file): the Level1Speller half of AC-K1 (on_result and on_label), AC-K3 (source "fusion" events, scan of
  the §4.3 rows and of one app run on clip D2), AC-K5 through the Speller, AC-K6 and the cases that kill the mutants
  R1 / R3 / R4 of review K1.
Pure logic on controlled inputs (chuỗi tạo có kiểm soát để kiểm logic); only TestClipEventsK3 needs the clip + checkpoint.
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


def _u_after_initial_consonant(tokens):
    """F3 condition written from the spec (not from the code): the last letter of the active syllable (tokens after the
    last SPACE) is "u" and ANOTHER letter stands before it in that syllable (tone tokens in between are not letters)."""
    start = max((i for i, t in enumerate(tokens) if t == SPACE), default=-1) + 1
    letters = [t for t in tokens[start:] if token_kind(t) == "letter"]
    return len(letters) >= 2 and letters[-1] == "u"


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
                if p == "ơ" and _u_after_initial_consonant(before):
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
        self.assertGreater(n_fused, 0)
        self.assertGreater(n_kept_f3, 0)


# =====================================================================================================================
# Step K2: fusion_target wired into Level1Speller (_apply via on_result, and on_label)
# =====================================================================================================================
FUSION_EVENT_KEYS = {"event", "action", "token", "source", "prediction", "confidence", "replaced", "index", "rule", "seq",
                     "t_ms", "tokens_after"}
CONF = 0.9


def _ok(p, conf=CONF):
    return {"status": "ok", "prediction": p, "confidence": conf}


def _emit(seq, p, action, conf=CONF):
    return LabelEmit(seq=seq, ts_ms=100.0 * seq, prediction=p, confidence=conf, action=action,
                     run_since_ms=100.0 * seq - 50.0, result=_ok(p, conf))


def _decoder_action(last_label, p):
    """The action Level1LabelDecoder gives (level1_segmenter: 'replace' when VARIANT_BASE[label] is the label emitted
    just before, else 'append')."""
    return "replace" if last_label is not None and level1_segmenter.VARIANT_BASE.get(p) == last_label else "append"


def run_speller(before, preds, path, unikey_mode=True):
    """Feeds `preds` (model labels, confidence CONF) to a Level1Speller holding `before`.
    path: 'result' = on_result; 'label' = on_label with action 'append'; 'decoder' = on_label with the decoder's action.
    Returns (speller, {seq: prediction}, [decision dicts]); seqs start at 1."""
    sp = Level1Speller(0.5, unikey_mode=unikey_mode)
    sp.tokens = list(before)
    preds_by_seq, decisions = {}, []
    last = before[-1] if before else None  # the tokens before were emitted by the decoder
    for k, p in enumerate(preds, start=1):
        preds_by_seq[k] = p
        if path == "result":
            decisions.extend(sp.on_result(k, _ok(p), 100.0 * k))
        else:
            action = "append" if path == "label" else _decoder_action(last, p)
            decisions.append(sp.on_label(k, _emit(k, p, action)))
        last = p
    return sp, preds_by_seq, decisions


SPELLER_PATHS = ("result", "label", "decoder")


class TestSpellerOracleK2(unittest.TestCase):
    """AC-K1, Level1Speller half: every row of §4.3 (same literal oracle) through on_result AND on_label."""

    def _check_rows(self, rows):
        for before, preds, after, text in rows:
            for path in SPELLER_PATHS:
                with self.subTest(before=before, preds=preds, path=path):
                    sp, _, _ = run_speller(before, preds, path)
                    if after is not None:
                        self.assertEqual(sp.tokens, after)
                    if text is not None:
                        self.assertEqual(sp.text, text)
                    self.assertEqual(sp.text, compose(sp.tokens)["text"])

    def test_15_pairs(self):
        self._check_rows(ORACLE_15_PAIRS)

    def test_spelling_rows(self):
        self._check_rows(ORACLE_SPELLING)

    def test_speller_equals_fusion_target(self):
        # the Speller applies exactly what fusion_target decides (no other letter rule in level1_core)
        for before, preds, _after, _text in ORACLE_15_PAIRS + ORACLE_SPELLING:
            for path in SPELLER_PATHS:
                with self.subTest(before=before, preds=preds, path=path):
                    sp, _, _ = run_speller(before, preds, path)
                    self.assertEqual(sp.tokens, apply_predictions(before, preds))

    def test_on_label_returns_replace_on_fusion(self):
        for before, pred, after in ((["b", "a"], "ô", ["b", "â"]), (["u"], "ơ", ["ư"]), (["d"], "đ", ["đ"]),
                                    (["b", "a", "dấu sắc"], "â", ["b", "â", "dấu sắc"])):
            with self.subTest(before=before, pred=pred):
                sp, _, decisions = run_speller(before, [pred], "label")
                self.assertEqual(sp.tokens, after)
                self.assertEqual(decisions[-1]["action"], "replace")
                self.assertTrue(decisions[-1]["accepted"])
        sp, _, decisions = run_speller(["b", "u"], ["ơ"], "label")  # F3: appended
        self.assertEqual(decisions[-1]["action"], "add")

    def test_low_confidence_is_never_fused(self):
        for path in ("result", "label"):
            sp = Level1Speller(0.5, unikey_mode=True)
            sp.tokens = ["b", "a"]
            if path == "result":
                sp.on_result(1, _ok("â", 0.3), 100.0)
            else:
                sp.on_label(1, _emit(1, "â", "append", 0.3))
            self.assertEqual(sp.tokens, ["b", "a"])
            self.assertEqual(sp.events[-1]["action"], "reject")


class TestFusionEventsK3(unittest.TestCase):
    """AC-K3: every fusion logs source 'fusion' with the F7 keys; no 'model' event has a token other than the model's
    prediction (scan of every event of the §4.3 rows)."""

    def _scan(self, sp, preds_by_seq, before):
        tokens = list(before)
        fusions = []
        for ev in sp.events:
            self.assertEqual(ev["event"], "token")
            if ev["source"] == "fusion":
                fusions.append(ev)
                self.assertEqual(set(ev), FUSION_EVENT_KEYS)
                self.assertEqual(ev["action"], "replace")
                self.assertEqual(ev["prediction"], preds_by_seq[ev["seq"]])
                self.assertEqual(ev["confidence"], CONF)
                self.assertEqual(ev["t_ms"], 100.0 * ev["seq"])
                idx = ev["index"]
                self.assertEqual(ev["replaced"], tokens[idx])
                self.assertEqual(ev["rule"], f"{tokens[idx]}+{ev['prediction']}")
                self.assertEqual(TABLE_15[ev["replaced"]][ev["prediction"]], ev["token"])
                n_tones = sum(token_kind(t) == "tone" for t in tokens)
                tokens[idx] = ev["token"]
                self.assertEqual(sum(token_kind(t) == "tone" for t in tokens), n_tones)
            elif ev["source"] == "model":
                self.assertNotIn("reason", ev)  # no word gap in these rows
                self.assertEqual(ev["token"], preds_by_seq[ev["seq"]], ev)
                if ev["action"] == "add":
                    tokens.append(ev["token"])
                elif ev["action"] == "replace":
                    idx = len(tokens) - 1 if ev["token"] not in TONE_MARKS else max(
                        i for i, t in enumerate(tokens) if t == ev["replaced"])
                    self.assertEqual(tokens[idx], ev["replaced"])
                    tokens[idx] = ev["token"]
            else:
                self.fail(f"unexpected source {ev['source']!r}")
            self.assertEqual(ev["tokens_after"], len(tokens))
        self.assertEqual(tokens, sp.tokens)  # the events replay to the final tokens
        return fusions

    def test_every_row_every_path(self):
        n_fusions = 0
        for before, preds, _after, _text in ORACLE_15_PAIRS + ORACLE_SPELLING:
            for path in SPELLER_PATHS:
                with self.subTest(before=before, preds=preds, path=path):
                    sp, preds_by_seq, _ = run_speller(before, preds, path)
                    fusions = self._scan(sp, preds_by_seq, before)
                    n_fusions += len(fusions)
                    if path != "decoder":  # every prediction either adds a token or is fused
                        self.assertEqual(len(fusions), len(before) + len(preds) - len(sp.tokens))
        self.assertGreater(n_fusions, 0)

    def test_literal_fusion_events(self):
        for path in ("result", "label"):
            with self.subTest(path=path):
                sp, _, _ = run_speller(["b", "a", "dấu sắc"], ["ô"], path)
                ev = sp.events[-1]
                self.assertEqual({k: ev[k] for k in ("action", "token", "source", "prediction", "replaced", "index",
                                                     "rule", "seq", "tokens_after")},
                                 {"action": "replace", "token": "â", "source": "fusion", "prediction": "ô",
                                  "replaced": "a", "index": 1, "rule": "a+ô", "seq": 1, "tokens_after": 3})
                sp, _, _ = run_speller(["u"], ["ơ"], path)
                ev = sp.events[-1]
                self.assertEqual((ev["source"], ev["token"], ev["prediction"], ev["replaced"], ev["index"], ev["rule"]),
                                 ("fusion", "ư", "ơ", "u", 0, "u+ơ"))
                sp, _, _ = run_speller(["b", "u"], ["ơ"], path)  # F3: the prediction itself, source model
                ev = sp.events[-1]
                self.assertEqual((ev["action"], ev["token"], ev["source"]), ("add", "ơ", "model"))

    def test_variant_base_branch_keeps_source_model(self):
        # the decoder's VARIANT_BASE replace (token == the model's label) stays source "model"
        sp = Level1Speller(0.5, unikey_mode=True)
        sp.on_label(1, _emit(1, "b", "append"))
        sp.on_label(2, _emit(2, "a", "append"))
        d = sp.on_label(3, _emit(3, "â", "replace"))
        self.assertEqual(sp.tokens, ["b", "â"])
        self.assertEqual(d["action"], "replace")
        ev = sp.events[-1]
        self.assertEqual((ev["action"], ev["token"], ev["source"], ev["replaced"]), ("replace", "â", "model", "a"))
        self.assertNotIn("rule", ev)


class TestMutationLocksK2(unittest.TestCase):
    """Cases that kill the mutants R1, R3, R4 of review K1 (fusion_target and through the Speller)."""

    def _both(self, before, pred, after):
        for path in ("result", "label"):
            with self.subTest(before=before, pred=pred, path=path):
                sp, _, _ = run_speller(before, [pred], path)
                self.assertEqual(sp.tokens, after)

    def test_r1_tone_between_initial_consonant_and_u(self):
        # F3 looks at every token before u in the syllable, not only the one just before it
        self.assertIsNone(fusion_target(["t", "dấu sắc", "u"], "ơ"))
        self.assertIsNone(fusion_target(["q", "dấu nặng", "dấu sắc", "u"], "ơ"))
        self.assertIsNone(fusion_target(["t", "dấu sắc", "u", "dấu hỏi"], "ơ"))
        self._both(["t", "dấu sắc", "u"], "ơ", ["t", "dấu sắc", "u", "ơ"])
        sp, _, _ = run_speller(["t", "dấu sắc", "u"], ["ơ"], "result")
        self.assertEqual(sp.text, "tuớ")

    def test_r3_tone_before_u_is_not_an_initial_consonant(self):
        self.assertEqual(fusion_target(["dấu sắc", "u"], "ơ"), (1, "ư", "u+ơ"))
        self.assertEqual(fusion_target(["b", SPACE, "dấu sắc", "u"], "ơ"), (3, "ư", "u+ơ"))
        self._both(["dấu sắc", "u"], "ơ", ["dấu sắc", "ư"])

    def test_r4_nfd_prediction_is_normalised(self):
        import unicodedata
        for pred in ("ô", "ơ", "â", "ư", "ă", "ê"):  # these labels have a decomposed (NFD) form
            self.assertNotEqual(unicodedata.normalize("NFD", pred), pred)
        o_hat = unicodedata.normalize("NFD", "ô")
        o_horn = unicodedata.normalize("NFD", "ơ")
        self.assertEqual(fusion_target(["b", "a"], o_hat), (1, "â", "a+ô"))
        self.assertEqual(fusion_target(["u"], o_horn), (0, "ư", "u+ơ"))
        self.assertEqual(fusion_target(["b", "o"], unicodedata.normalize("NFD", "ư")), (1, "ơ", "o+ư"))
        self.assertIsNone(fusion_target(["b", "u"], o_horn))  # F3 also on the NFD form
        self._both(["b", "a"], o_hat, ["b", "â"])
        self._both(["u"], o_horn, ["ư"])


class TestUnikeyOffK6(unittest.TestCase):
    """AC-K6: unikey_mode=False -> M0 behaviour (every accepted label appended, no fusion event)."""

    def test_rows_append_everything(self):
        for before, preds, _after, _text in ORACLE_15_PAIRS + ORACLE_SPELLING:
            for path in ("result", "label"):
                with self.subTest(before=before, preds=preds, path=path):
                    sp, _, _ = run_speller(before, preds, path, unikey_mode=False)
                    self.assertEqual(sp.tokens, list(before) + list(preds))
                    self.assertFalse(any(e["source"] == "fusion" for e in sp.events))


class TestSpellerRandomK5(unittest.TestCase):
    """AC-K5 through Level1Speller: 200 random sequences (fixed seed, 34 classes + SPACE); after EVERY operation
    text == compose(tokens)["text"]; a fusion keeps the number of tone tokens. Half the sequences go through on_result,
    half through on_label (decoder action); SPACE is the space key. The expected tokens come from the spec (F1-F3 and
    the in-place tone replacement of unikey mode), written here independently of level1_unikey."""

    SEED = 20261010
    N_SEQUENCES = 200
    MAX_LEN = 40

    @staticmethod
    def _expected(before, p):
        start = max((i for i, t in enumerate(before) if t == SPACE), default=-1) + 1
        if p == SPACE:
            return before + [SPACE] if before else list(before)
        if p in TONE_MARKS:
            tones = [i for i in range(start, len(before)) if before[i] in TONE_MARKS]
            if tones:
                out = list(before)
                out[tones[-1]] = p
                return out
            return before + [p]
        letters = [i for i in range(start, len(before)) if token_kind(before[i]) == "letter"]
        if letters:
            i = letters[-1]
            base = before[i]
            if p in TABLE_15.get(base, {}) and not (base == "u" and p == "ơ" and len(letters) >= 2):
                out = list(before)
                out[i] = TABLE_15[base][p]
                return out
        return before + [p]

    def test_random_sequences_through_speller(self):
        vocab = list(LETTERS) + list(TONE_MARKS)
        self.assertEqual(len(vocab), 34)
        vocab.append(SPACE)
        rng = random.Random(self.SEED)
        n_fused = n_kept_f3 = n_tone_kept = 0
        for n in range(self.N_SEQUENCES):
            sp = Level1Speller(0.5, unikey_mode=True)
            via_label = n % 2 == 1
            last = None
            for k in range(1, rng.randint(1, self.MAX_LEN) + 1):
                p = rng.choice(vocab)
                before = list(sp.tokens)
                n_ev = len(sp.events)
                if p == SPACE:
                    sp.key("space", 100.0 * k)
                elif via_label:
                    sp.on_label(k, _emit(k, p, _decoder_action(last, p)))
                    last = p
                else:
                    sp.on_result(k, _ok(p), 100.0 * k)
                self.assertEqual(sp.text, compose(sp.tokens)["text"], (n, before, p))
                self.assertEqual(sp.tokens, self._expected(before, p), (n, before, p))
                if p == "ơ" and _u_after_initial_consonant(before):
                    n_kept_f3 += 1
                for ev in sp.events[n_ev:]:
                    if ev["source"] == "fusion":
                        n_fused += 1
                        self.assertEqual(len(sp.tokens), len(before))
                        self.assertEqual(sum(t in TONE_MARKS for t in sp.tokens), sum(t in TONE_MARKS for t in before))
                        n_tone_kept += sum(t in TONE_MARKS for t in before) > 0
                    elif ev["source"] == "model":
                        self.assertEqual(ev["token"], p)
        self.assertGreater(n_fused, 0)
        self.assertGreater(n_kept_f3, 0)
        self.assertGreater(n_tone_kept, 0)


class TestOneTableK4(unittest.TestCase):
    """AC-K4: one `DIACRITIC_FUSION = {` in src/ (level1_segmenter.py); level1_core keeps no copy of its own."""

    def test_single_table_definition(self):
        hits = []
        for root, _dirs, files in os.walk(os.path.join(PROJECT_ROOT, "src")):
            for name in files:
                if name.endswith(".py"):
                    path = os.path.join(root, name)
                    with open(path, encoding="utf-8") as f:
                        n = f.read().count("DIACRITIC_FUSION = {")
                    if n:
                        hits.append((os.path.relpath(path, PROJECT_ROOT).replace(os.sep, "/"), n))
        self.assertEqual(hits, [("src/inference/level1_segmenter.py", 1)])

    def test_core_uses_the_segmenter_table(self):
        from src.inference import level1_core
        table = getattr(level1_core, "DIACRITIC_FUSION", level1_segmenter.DIACRITIC_FUSION)
        self.assertIs(table, level1_segmenter.DIACRITIC_FUSION)


CLIP_D2 = os.path.join("data", "external", "hauuto_raw", "raw", "raw", "hau", "a_hau_A_001.mp4")
CKPT = os.path.join("checkpoints", "alphabet_best.pt")
DEMO_CONFIG = os.path.join("configs", "level1_demo_classifier_rev9.json")
_MISSING = [p for p in (CLIP_D2, CKPT) if not os.path.exists(os.path.join(PROJECT_ROOT, p))]


@unittest.skipUnless(not _MISSING, "missing (gitignored data / checkpoint): " + ", ".join(_MISSING))
class TestClipEventsK3(unittest.TestCase):
    """AC-K3 on one app run (clip D2, demo config rev9, unikey on by default): no event with source 'model' has a token
    other than the model's prediction of the same seq (word-gap spaces have no prediction and carry reason 'word_gap')."""

    def test_clip_d2_model_events_are_predictions(self):
        import level1_demo as app_mod
        args = app_mod.build_parser().parse_args(["--source", CLIP_D2, "--headless", "--config", DEMO_CONFIG])
        self.assertTrue(args.unikey_mode)
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            report = app_mod.Level1App(args).run()
        finally:
            os.chdir(cwd)
        self.assertEqual(report["rearm_mode"], "classifier")
        preds = {e["seq"]: e["prediction"] for e in report["labels"]}
        tokens = [e for e in report["events"] if e.get("event") == "token"]
        model = [e for e in tokens if e["source"] == "model" and e.get("reason") != "word_gap"]
        self.assertGreater(len(model), 0)
        for ev in model:
            self.assertEqual(ev["token"], preds[ev["seq"]], ev)
        for ev in tokens:
            if ev["source"] == "fusion":
                self.assertEqual(ev["prediction"], preds[ev["seq"]], ev)
                self.assertEqual(set(ev), FUSION_EVENT_KEYS)
        self.assertEqual(report["text"], compose(report["tokens"])["text"])


if __name__ == "__main__":
    unittest.main()
