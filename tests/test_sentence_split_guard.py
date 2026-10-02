"""Plan 13 (decision Q1 = (ii), 2026-10-02 10:05) — sentence split v1 + leak guard for CSLR / ViT5.

G1 (always runs, tiny hand-written fixtures in a scratch dir under `<repo>/_work/_test_tmp/`, no GPU, no network):
  - `load_sentence_split` rejects overlapping / incomplete / wrongly sized splits and a test set != SENT271..SENT300;
  - `select_vslgh_samples` never returns a sample outside the sentence list or outside the signer split;
  - `match_heldout` catches L1, L2 and near-duplicate matches on the source AND on the target side;
  - `make_split_dict` is deterministic and follows the registered rule (val = sorted(Random(42).sample(SENT001..270, 30))).

These tests FAIL (never skip) on a violation. Fixture data are synthetic on purpose: they test the guard logic, not a model.
"""
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.data import sentence_split as SS  # noqa: E402

SCRATCH_PARENT = os.path.join(ROOT, "_work", "_test_tmp")
MAKE_SCRIPT = os.path.join(ROOT, "scripts", "make_vslgh_sentence_split.py")

ALL_IDS = [f"SENT{i:03d}" for i in range(1, 301)]
TEST_IDS = ALL_IDS[270:]
SIGNERS = {"S01": "train", "S02": "train", "S03": "train", "S04": "train", "S05": "val", "S06": "test"}


def fake_canonical():
    """300 sentences x 6 signers; S01-S04 with 3 repetitions (as the real layout), S05/S06 with 1."""
    items = []
    for sid in ALL_IDS:
        for signer, split in SIGNERS.items():
            reps = 3 if split == "train" else 1
            for r in range(1, reps + 1):
                items.append({
                    "id": f"{sid}_{signer}_R{r:02d}_F",
                    "sentence_id": sid,
                    "signer_id": signer,
                    "split": split,
                    "gloss_sequence": [f"G{sid[4:]}", "CHUNG"],
                    "translation": f"Đây là câu mẫu số {sid[4:]}.",
                })
    return items


def valid_split_dict():
    return SS.make_split_dict(fake_canonical(), seed=42)


class _Scratch(unittest.TestCase):
    def setUp(self):
        os.makedirs(SCRATCH_PARENT, exist_ok=True)
        self._td = tempfile.TemporaryDirectory(dir=SCRATCH_PARENT, prefix="sentsplit_")
        self.tmp = self._td.name

    def tearDown(self):
        self._td.cleanup()

    def p(self, *parts):
        return os.path.join(self.tmp, *parts)

    def write_json(self, name, obj):
        path = self.p(name)
        with open(path, "wb") as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8"))
        return path


class TestG1MakeAndLoad(_Scratch):
    def test_make_split_follows_registered_rule(self):
        d = valid_split_dict()
        self.assertEqual(d["seed"], 42)
        self.assertEqual(d["test_ids"], TEST_IDS)
        expected_val = sorted(random.Random(42).sample(sorted(ALL_IDS[:270]), 30))
        self.assertEqual(d["val_ids"], expected_val)
        self.assertEqual(d["train_ids"], sorted(set(ALL_IDS) - set(TEST_IDS) - set(expected_val)))
        self.assertEqual(len(d["train_ids"]), 240)
        self.assertEqual(d["signer_split"], {"train": ["S01", "S02", "S03", "S04"], "val": ["S05"], "test": ["S06"]})
        self.assertEqual(d["version"], SS.SPLIT_VERSION)

    def test_make_split_deterministic_and_seed_sensitive(self):
        self.assertEqual(SS.make_split_dict(fake_canonical(), seed=42), SS.make_split_dict(fake_canonical(), seed=42))
        self.assertNotEqual(SS.make_split_dict(fake_canonical(), seed=7)["val_ids"], valid_split_dict()["val_ids"])

    def test_make_split_rejects_wrong_canonical_layout(self):
        items = fake_canonical()
        items[0] = dict(items[0], split="val")  # an S01 clip labelled val: signer <-> split mapping broken
        with self.assertRaises(ValueError):
            SS.make_split_dict(items, seed=42)
        items = [s for s in fake_canonical() if s["sentence_id"] != "SENT150"]  # 299 sentences
        with self.assertRaises(ValueError):
            SS.make_split_dict(items, seed=42)
        items = fake_canonical() + [dict(fake_canonical()[0], id="X", signer_id="S07", split="train")]
        with self.assertRaises(ValueError):
            SS.make_split_dict(items, seed=42)

    def test_load_valid(self):
        path = self.write_json("split.json", valid_split_dict())
        s = SS.load_sentence_split(path)
        self.assertEqual(len(s.train_ids), 240)
        self.assertEqual(len(s.val_ids), 30)
        self.assertEqual(list(s.test_ids), TEST_IDS)
        self.assertEqual(s.ids("test"), frozenset(TEST_IDS))
        self.assertEqual(len(s.sha256), 64)
        self.assertTrue(s.ids("train").isdisjoint(s.ids("val") | s.ids("test")))

    def _assert_rejected(self, d):
        path = self.write_json("bad.json", d)
        with self.assertRaises(ValueError):
            SS.load_sentence_split(path)
        with self.assertRaises(ValueError):
            SS.validate_split_dict(d)

    def test_load_rejects_test_id_in_train(self):
        d = valid_split_dict()
        d["train_ids"] = sorted(d["train_ids"] + ["SENT271"])  # leak: overlap train/test
        self._assert_rejected(d)

    def test_load_rejects_val_test_overlap(self):
        d = valid_split_dict()
        d["val_ids"] = sorted(d["val_ids"][1:] + ["SENT300"])
        self._assert_rejected(d)

    def test_load_rejects_train_val_overlap(self):
        d = valid_split_dict()
        moved = d["val_ids"][0]
        d["train_ids"] = sorted(d["train_ids"][1:] + [moved])  # keeps 240 but now overlaps val, misses one id
        self._assert_rejected(d)

    def test_load_rejects_missing_coverage(self):
        d = valid_split_dict()
        d["train_ids"] = d["train_ids"][:-1]
        self._assert_rejected(d)

    def test_load_rejects_wrong_sizes(self):
        d = valid_split_dict()
        moved = d["train_ids"][0]
        d["train_ids"] = d["train_ids"][1:]
        d["val_ids"] = sorted(d["val_ids"] + [moved])  # 239 / 31 / 30, still disjoint and covering
        self._assert_rejected(d)

    def test_load_rejects_test_not_sent271_300(self):
        d = valid_split_dict()
        swap_in = d["train_ids"][0]
        d["train_ids"] = sorted(d["train_ids"][1:] + ["SENT271"])
        d["test_ids"] = sorted([swap_in] + TEST_IDS[1:])  # 240/30/30, disjoint, covering, but T != SENT271..300
        self._assert_rejected(d)

    def test_load_rejects_unknown_ids_duplicates_and_bad_signers(self):
        d = valid_split_dict()
        d["train_ids"] = d["train_ids"][:-1] + ["SENT999"]
        self._assert_rejected(d)
        d = valid_split_dict()
        d["val_ids"] = d["val_ids"][:-1] + [d["val_ids"][0]]
        self._assert_rejected(d)
        d = valid_split_dict()
        d["signer_split"] = {"train": ["S01", "S02", "S03", "S04", "S06"], "val": ["S05"], "test": ["S06"]}
        self._assert_rejected(d)
        d = valid_split_dict()
        d["version"] = "something_else"
        self._assert_rejected(d)

    def test_sha256_is_lf_bytes_and_crlf_checkout_invariant(self):
        # A Windows checkout with core.autocrlf=true turns the LF file into CRLF; the identity must not change.
        data = SS.split_file_bytes(valid_split_dict())
        self.assertNotIn(b"\r", data)
        lf, crlf = self.p("lf.json"), self.p("crlf.json")
        with open(lf, "wb") as f:
            f.write(data)
        with open(crlf, "wb") as f:
            f.write(data.replace(b"\n", b"\r\n"))
        expected = hashlib.sha256(data).hexdigest()
        self.assertEqual(SS.load_sentence_split(lf).sha256, expected)
        self.assertEqual(SS.load_sentence_split(crlf).sha256, expected)
        # ...but any content change does change it
        d = valid_split_dict()
        d["seed"] = 43
        with open(self.p("other.json"), "wb") as f:
            f.write(SS.split_file_bytes(d))
        self.assertNotEqual(SS.load_sentence_split(self.p("other.json")).sha256, expected)

    def test_resolve_accepts_path_or_object(self):
        path = self.write_json("split.json", valid_split_dict())
        s = SS.load_sentence_split(path)
        self.assertIs(SS.resolve_sentence_split(s), s)
        self.assertEqual(SS.resolve_sentence_split(path).train_ids, s.train_ids)


class TestG1Select(_Scratch):
    def setUp(self):
        super().setUp()
        self.split = SS.load_sentence_split(self.write_json("split.json", valid_split_dict()))
        self.items = fake_canonical()

    def test_select_respects_sentences_and_signers(self):
        tr = SS.select_vslgh_samples(self.items, "train", self.split)
        va = SS.select_vslgh_samples(self.items, "val", self.split)
        te = SS.select_vslgh_samples(self.items, "test", self.split)
        self.assertEqual(len(tr), 240 * 4 * 3)
        self.assertEqual(len(va), 30)
        self.assertEqual(len(te), 30)
        self.assertEqual({s["signer_id"] for s in tr}, {"S01", "S02", "S03", "S04"})
        self.assertEqual({s["signer_id"] for s in va}, {"S05"})
        self.assertEqual({s["signer_id"] for s in te}, {"S06"})
        self.assertEqual({s["sentence_id"] for s in tr}, self.split.ids("train"))
        self.assertEqual({s["sentence_id"] for s in va}, self.split.ids("val"))
        self.assertEqual(sorted(s["sentence_id"] for s in te), TEST_IDS)
        for s in tr + va:
            self.assertNotIn(s["sentence_id"], self.split.ids("test"))
        for s in tr:
            self.assertNotIn(s["sentence_id"], self.split.ids("val"))
        # original order is preserved
        tr_ids = {s["id"] for s in tr}
        self.assertEqual([s["id"] for s in tr], [s["id"] for s in self.items if s["id"] in tr_ids])

    def test_select_rejects_inconsistent_signer_split(self):
        items = list(self.items)
        idx = next(i for i, s in enumerate(items) if s["signer_id"] == "S06")
        items[idx] = dict(items[idx], split="train")  # S06 clip mislabelled train -> must not leak silently
        with self.assertRaises(ValueError):
            SS.select_vslgh_samples(items, "train", self.split)
        items = list(self.items)
        idx = next(i for i, s in enumerate(items) if s["signer_id"] == "S05")
        items[idx] = dict(items[idx], split="test")
        with self.assertRaises(ValueError):
            SS.select_vslgh_samples(items, "val", self.split)

    def test_select_rejects_unknown_split_name(self):
        for name in ("all", None, "TRAIN"):
            with self.assertRaises(ValueError):
                SS.select_vslgh_samples(self.items, name, self.split)


class TestG1MatchHeldout(unittest.TestCase):
    CANON = [
        {"sentence_id": "SENT271", "signer_id": "S01", "split": "train",
         "gloss_sequence": ["TÔI", "ĐĂNG-KÝ", "KHÁM", "SỨC-KHỎE", "MUỐN"], "translation": "Tôi muốn đăng ký khám sức khỏe."},
        {"sentence_id": "SENT271", "signer_id": "S06", "split": "test",
         "gloss_sequence": ["TÔI", "MUỐN", "ĐĂNG-KÝ", "KHÁM"], "translation": "Tôi muốn đăng ký khám bệnh."},
        {"sentence_id": "SENT272", "signer_id": "S02", "split": "train",
         "gloss_sequence": ["BẠN", "TÊN", "GÌ"], "translation": "Bạn tên là gì?"},
        {"sentence_id": "SENT001", "signer_id": "S01", "split": "train",
         "gloss_sequence": ["MÈO", "ĂN", "CÁ"], "translation": "Con mèo ăn cá."},
    ]

    def setUp(self):
        self.h = SS.heldout_texts(self.CANON, ["SENT271", "SENT272"])

    def check(self, src, tgt, rule, side, sid):
        ok, reason = SS.match_heldout(src, tgt, self.h)
        self.assertTrue(ok, (src, tgt))
        self.assertEqual(reason["rule"], rule)
        self.assertEqual(reason["side"], side)
        self.assertIn(sid, reason["sentence_ids"])

    def test_l1_source_and_target(self):
        # L1 = equal after the training normalisers (normalize_vsl_source lower-cases and drops hyphens).
        self.check("tôi đăng ký khám sức khỏe muốn", "Một câu khác hẳn.", "L1", "source", "SENT271")
        self.check("xyz", "Bạn tên là gì?", "L1", "target", "SENT272")
        # every repetition / signer of the sentence counts, not only the first sample
        self.check("TÔI MUỐN ĐĂNG-KÝ KHÁM", "khác", "L1", "source", "SENT271")

    def test_l2_source_and_target(self):
        # L2 = L1 + lower-case + drop .,!?;:"'()[]{}… + collapse spaces. Target: case and final punctuation differ.
        self.check("hoàn toàn khác", "tôi muốn đăng ký khám sức khỏe", "L2", "target", "SENT271")
        self.check("hoàn toàn khác", "BẠN TÊN LÀ GÌ…", "L2", "target", "SENT272")
        # Source side: "…" is not removed by normalize_vsl_source, but is by L2.
        self.check("bạn tên gì…", "khác", "L2", "source", "SENT272")

    def test_near_duplicate_source_and_target(self):
        # 8 words vs 7 words; Jaccard 7/8 >= 0.8, word-count difference 1.
        self.check("tôi đăng ký khám sức khỏe muốn nhanh", "khác", "near_dup", "source", "SENT271")
        self.check("abc", "Tôi rất muốn đăng ký khám sức khỏe.", "near_dup", "target", "SENT271")

    def test_near_duplicate_boundaries(self):
        h = SS.heldout_texts([{"sentence_id": "SENT271", "gloss_sequence": ["A", "B", "C", "D"],
                               "translation": "a b c d e"}], ["SENT271"])
        # source a b c d vs a b c d x: J = 4/5 = 0.8 (>= 0.8), count diff 1 -> match
        ok, reason = SS.match_heldout("a b c d x", "zzz", h)
        self.assertTrue(ok)
        self.assertEqual(reason["rule"], "near_dup")
        # a b c x vs a b c d: J = 3/5 = 0.6 -> no
        self.assertFalse(SS.match_heldout("a b c x", "zzz", h)[0])
        # target a b c d e vs a b c d e f g: J = 5/7 < 0.8 and diff 2 -> no
        self.assertFalse(SS.match_heldout("qqq", "a b c d e f g", h)[0])
        # target a b c d e vs a b c d e e e: same word set (J = 1) but word count diff 2 -> no
        self.assertFalse(SS.match_heldout("qqq", "a b c d e e e", h)[0])

    def test_no_match_and_other_sentences_ignored(self):
        ok, reason = SS.match_heldout("trời hôm nay đẹp", "Hôm nay trời đẹp.", self.h)
        self.assertFalse(ok)
        self.assertIsNone(reason)
        # SENT001 is not held out: its exact pair must not match
        self.assertFalse(SS.match_heldout("MÈO ĂN CÁ", "Con mèo ăn cá.", self.h)[0])

    def test_rule_priority_l1_before_l2_before_near_dup(self):
        ok, reason = SS.match_heldout("tôi đăng ký khám sức khỏe muốn", "Tôi muốn đăng ký khám sức khỏe.", self.h)
        self.assertTrue(ok)
        self.assertEqual((reason["rule"], reason["side"]), ("L1", "source"))

    def test_heldout_rejects_unknown_ids(self):
        with self.assertRaises(ValueError):
            SS.heldout_texts(self.CANON, ["SENT299"])

    def test_l2_definition(self):
        self.assertEqual(SS.l2_text('  Tôi, "Bạn" (và) [họ]… ĐI!  '), "tôi bạn và họ đi")


class TestG1MakeScript(_Scratch):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, MAKE_SCRIPT, *args], capture_output=True, text=True, encoding="utf-8")

    def test_cli_writes_lf_and_refuses_overwrite(self):
        canon = self.write_json("dataset_canonical.json", fake_canonical())
        out = self.p("cfg", "split.json")
        res = self.run_cli("--canonical", canon, "--seed", "42", "--out", out)
        self.assertEqual(res.returncode, 0, res.stderr)
        with open(out, "rb") as f:
            data = f.read()
        self.assertNotIn(b"\r", data)
        self.assertTrue(data.endswith(b"\n"))
        loaded = SS.load_sentence_split(out)
        self.assertEqual(list(loaded.val_ids), valid_split_dict()["val_ids"])
        info = json.loads(res.stdout)
        self.assertEqual(info["sha256"], loaded.sha256)
        # regenerating into another file gives identical bytes
        out2 = self.p("cfg", "split2.json")
        self.assertEqual(self.run_cli("--canonical", canon, "--seed", "42", "--out", out2).returncode, 0)
        with open(out2, "rb") as f:
            self.assertEqual(f.read(), data)
        # existing target -> exit 2, untouched
        res = self.run_cli("--canonical", canon, "--seed", "42", "--out", out)
        self.assertEqual(res.returncode, 2)
        with open(out, "rb") as f:
            self.assertEqual(f.read(), data)

    def test_cli_bad_canonical(self):
        items = [s for s in fake_canonical() if s["sentence_id"] != "SENT300"]
        canon = self.write_json("dataset_canonical.json", items)
        res = self.run_cli("--canonical", canon, "--seed", "42", "--out", self.p("s.json"))
        self.assertNotEqual(res.returncode, 0)
        self.assertFalse(os.path.exists(self.p("s.json")))
        res = self.run_cli("--canonical", self.p("missing.json"), "--seed", "42", "--out", self.p("s.json"))
        self.assertEqual(res.returncode, 2)
        self.assertFalse(os.path.exists(self.p("s.json")))


# =====================================================================================================================
# B2b — dataset options (`sentence_split` / `exclude_heldout`). G1 part: fake data; default (None) = old behaviour.
# =====================================================================================================================

def fake_10k_rows():
    """Tiny 10k-style corpus. Sentences of the fake canonical: source "G<num> CHUNG", target "Đây là câu mẫu số <num>."."""
    rows = [
        ("G271 CHUNG", "Không liên quan ."),                 # L1 source == SENT271 (T)
        ("Trời mưa .", "Đây là câu mẫu số 280."),             # L1 target == SENT280 (T)
        ("Trời nắng .", "đây là câu mẫu số 285"),             # L2 target == SENT285 (T)
        ("Mèo ăn cá .", "Đây là câu mẫu số 290 nhé."),        # near_dup target (7 vs 6 words, J 6/7) SENT290 (T)
        ("G002 CHUNG", "Gì đó ."),                           # L1 source == SENT002 (V for seed 42)
        ("G001 CHUNG", "Đây là câu mẫu số 001."),             # SENT001 is train -> kept
        ("Đây là câu mẫu số 001 nhé", "Một hai ."),           # near-dup of a TRAIN sentence only -> kept
    ]
    rows += [(f"Câu khác {i} .", f"Một câu khác số {i} .") for i in range(13)]
    return [{"id": f"PAR_10K_{i + 1:05d}", "vsl": v, "vi": t} for i, (v, t) in enumerate(rows)]


EXPECTED_EXCLUDED = {"PAR_10K_00001": ("L1", "source", "SENT271"), "PAR_10K_00002": ("L1", "target", "SENT280"),
                     "PAR_10K_00003": ("L2", "target", "SENT285"), "PAR_10K_00004": ("near_dup", "target", "SENT290"),
                     "PAR_10K_00005": ("L1", "source", "SENT002")}


def old_clean10k_split(rows, split, val_ratio=0.1, seed=42):
    """The pre-plan-13 split of Clean10kDataset, re-stated independently (90/10 after random.Random(seed).shuffle)."""
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    val_size = int(len(shuffled) * val_ratio)
    return shuffled[:val_size] if split == "val" else shuffled[val_size:]


class TestB2bDatasetOptions(_Scratch):
    def setUp(self):
        super().setUp()
        self.items = fake_canonical()
        self.canon = self.write_json("dataset_canonical.json", self.items)
        os.makedirs(self.p("kp"), exist_ok=True)
        self.split_path = self.write_json("split.json", valid_split_dict())
        self.split = SS.load_sentence_split(self.split_path)
        self.jsonl = self.p("10k.jsonl")
        with open(self.jsonl, "wb") as f:
            for r in fake_10k_rows():
                f.write((json.dumps(r, ensure_ascii=False) + "\n").encode("utf-8"))

    # ---- VSLGHContinuousDataset ------------------------------------------------------------------------------------
    def cont(self, **kw):
        from src.data.vsl_gh_dataset import VSLGHContinuousDataset
        return VSLGHContinuousDataset(canonical_json=self.canon, keypoints_dir=self.p("kp"), **kw)

    def test_continuous_default_unchanged(self):
        for split in (None, "train", "val", "test"):
            ds = self.cont(split=split)
            self.assertEqual([s["id"] for s in ds.samples],
                             [s["id"] for s in self.items if split is None or s["split"] == split], split)
            self.assertIsNone(ds.sentence_split)
            # default vocabulary still from the WHOLE canonical file (old behaviour)
            self.assertIn("G271", ds.vocab.gloss_to_id)
        ds_tr = self.cont(loso_signer="S03", loso_mode="train")
        ds_te = self.cont(loso_signer="S03", loso_mode="test")
        self.assertEqual([s["id"] for s in ds_tr.samples], [s["id"] for s in self.items if s["signer_id"] != "S03"])
        self.assertEqual([s["id"] for s in ds_te.samples], [s["id"] for s in self.items if s["signer_id"] == "S03"])

    def test_continuous_sentence_split(self):
        for name in ("train", "val", "test"):
            for arg in (self.split_path, self.split):
                ds = self.cont(split=name, sentence_split=arg)
                self.assertEqual([s["id"] for s in ds.samples],
                                 [s["id"] for s in SS.select_vslgh_samples(self.items, name, self.split)])
        tr = self.cont(split="train", sentence_split=self.split_path)
        va = self.cont(split="val", sentence_split=self.split_path)
        te = self.cont(split="test", sentence_split=self.split_path)
        self.assertEqual((len(tr), len(va), len(te)), (240 * 4 * 3, 30, 30))
        self.assertTrue({s["sentence_id"] for s in tr.samples}.isdisjoint(self.split.ids("val") | self.split.ids("test")))
        self.assertTrue({s["sentence_id"] for s in va.samples}.isdisjoint(self.split.ids("test")))
        self.assertEqual(sorted(s["sentence_id"] for s in te.samples), TEST_IDS)
        self.assertEqual({s["signer_id"] for s in te.samples}, {"S06"})

    def test_continuous_sentence_split_vocab_train_only(self):
        ds = self.cont(split="val", sentence_split=self.split_path)
        expected = {"<blank>", "<unk>", "CHUNG"} | {f"G{sid[4:]}" for sid in self.split.train_ids}
        self.assertEqual(set(ds.vocab.gloss_to_id), expected)
        for sid in self.split.val_ids + self.split.test_ids:
            self.assertNotIn(f"G{sid[4:]}", ds.vocab.gloss_to_id)
        # an explicit vocabulary always wins (train_cslr.py passes the vocab file)
        from src.data.vsl_gh_dataset import VSLGlossVocabulary
        v = VSLGlossVocabulary(tokens=["X"])
        self.assertIs(self.cont(split="train", sentence_split=self.split_path, vocabulary=v).vocab, v)

    def test_continuous_sentence_split_rejects_bad_args(self):
        for split in (None, "all"):
            with self.assertRaises(ValueError):
                self.cont(split=split, sentence_split=self.split_path)
        with self.assertRaises(ValueError):
            self.cont(split="train", loso_signer="S01", loso_mode="train", sentence_split=self.split_path)
        bad = valid_split_dict()
        bad["train_ids"] = sorted(bad["train_ids"] + ["SENT271"])
        with self.assertRaises(ValueError):
            self.cont(split="train", sentence_split=self.write_json("bad.json", bad))

    # ---- VSLGHTextDataset ------------------------------------------------------------------------------------------
    def text(self, **kw):
        from src.translation.dataset import VSLGHTextDataset
        return VSLGHTextDataset(canonical_json=self.canon, **kw)

    def test_text_default_unchanged(self):
        expected = {"train": ALL_IDS[:240], "val": ALL_IDS[240:270], "test": ALL_IDS[270:], "all": ALL_IDS}
        for split, ids in expected.items():
            self.assertEqual([s["sentence_id"] for s in self.text(split=split).samples], ids)
        with self.assertRaises(ValueError):
            self.text(split="bogus")

    def test_text_sentence_split(self):
        from src.translation.text_normalizer import normalize_vietnamese_target, normalize_vsl_source
        for name in ("train", "val", "test"):
            ds = self.text(split=name, sentence_split=self.split_path)
            self.assertEqual([s["sentence_id"] for s in ds.samples], list(getattr(self.split, f"{name}_ids")))
        self.assertEqual([s["sentence_id"] for s in self.text(split="all", sentence_split=self.split_path).samples], ALL_IDS)
        tr = self.text(split="train", sentence_split=self.split)
        self.assertTrue({s["sentence_id"] for s in tr.samples}.isdisjoint(set(self.split.heldout_ids())))
        first = next(s for s in self.items if s["sentence_id"] == tr.samples[0]["sentence_id"])
        self.assertEqual(tr.samples[0]["source"], normalize_vsl_source(first["gloss_sequence"]))
        self.assertEqual(tr.samples[0]["target"], normalize_vietnamese_target(first["translation"]))
        with self.assertRaises(ValueError):
            self.text(split="bogus", sentence_split=self.split_path)

    # ---- Clean10kDataset -------------------------------------------------------------------------------------------
    def c10k(self, **kw):
        from src.translation.dataset import Clean10kDataset
        return Clean10kDataset(jsonl_path=self.jsonl, **kw)

    def test_clean10k_default_unchanged(self):
        rows = fake_10k_rows()
        for split in ("train", "val"):
            ds = self.c10k(split=split)
            self.assertEqual([s["id"] for s in ds.samples], [r["id"] for r in old_clean10k_split(rows, split)])
            self.assertEqual([p[0] for p in ds.normalized_pairs], [r["id"] for r in old_clean10k_split(rows, split)])
            self.assertEqual(ds.excluded, [])

    def test_clean10k_exclude_heldout(self):
        rows = fake_10k_rows()
        heldout = SS.heldout_texts(self.items, self.split.heldout_ids())
        seen_excluded = {}
        for split in ("train", "val"):
            old = [r["id"] for r in old_clean10k_split(rows, split)]
            ds = self.c10k(split=split, exclude_heldout=heldout)
            kept = [s["id"] for s in ds.samples]
            self.assertEqual([p[0] for p in ds.normalized_pairs], kept)
            self.assertEqual(ds.excluded_ids, [e["id"] for e in ds.excluded])
            # nothing is added, order kept, kept + excluded == the old split
            self.assertEqual(kept, [i for i in old if i not in set(ds.excluded_ids)])
            self.assertEqual(sorted(kept + ds.excluded_ids), sorted(old))
            for item in ds:
                self.assertFalse(SS.match_heldout(item["source"], item["target"], heldout)[0], item)
            for e in ds.excluded:
                seen_excluded[e["id"]] = (e["rule"], e["side"], e["sentence_ids"][0])
        self.assertEqual(seen_excluded, EXPECTED_EXCLUDED)

    def test_clean10k_exclude_requires_heldout_object(self):
        with self.assertRaises(TypeError):
            self.c10k(split="train", exclude_heldout=["SENT271"])


# =====================================================================================================================
# G2 — real local data (configs/vslgh_sentence_split_v1.json is tracked; VSL-GH / 10k data are local, untracked).
# Missing DATA -> skip with the reason (plan 13: present after B11, where AC8-c demands 0 skip); a violation -> FAIL.
# Overrides (only for mutation checks on COPIES under _work/, plan 13 AC11-c): VSLT_GUARD_SPLIT, VSLT_GUARD_CANONICAL,
# VSLT_GUARD_CLEAN10K.
# =====================================================================================================================

REAL_SPLIT = os.environ.get("VSLT_GUARD_SPLIT", os.path.join(ROOT, "configs", "vslgh_sentence_split_v1.json"))
REAL_CANON = os.environ.get("VSLT_GUARD_CANONICAL", os.path.join(ROOT, "data", "external", "vsl_gh", "dataset_canonical.json"))
REAL_KP = os.path.join(ROOT, "data", "external", "vsl_gh", "keypoints_frontal")
REAL_CLEAN10K = os.environ.get("VSLT_GUARD_CLEAN10K",
                               os.path.join(ROOT, "data", "external", "parallel_text", "vie_vsl_10k_cleaned.jsonl"))


class TestG2RealData(_Scratch):
    @classmethod
    def setUpClass(cls):
        # The split file is tracked: missing or invalid is a FAILURE, never a skip.
        cls.split = SS.load_sentence_split(REAL_SPLIT)

    def need(self, path):
        if not os.path.exists(path):
            self.skipTest(f"local data not present: {path} (restored data; required from plan 13 B11)")

    def load_canon(self):
        self.need(REAL_CANON)
        with open(REAL_CANON, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_split_file_regenerates_identically(self):
        self.need(REAL_CANON)
        out = self.p("regen.json")
        res = subprocess.run([sys.executable, MAKE_SCRIPT, "--canonical", REAL_CANON, "--seed", str(self.split.seed),
                              "--out", out], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 0, res.stderr)
        with open(out, "rb") as f:
            regen = f.read()
        with open(REAL_SPLIT, "rb") as f:
            committed = f.read().replace(b"\r\n", b"\n")  # Windows autocrlf checkout; the git blob is LF
        self.assertEqual(regen, committed)
        self.assertEqual(hashlib.sha256(regen).hexdigest(), self.split.sha256)

    def test_cslr_dataset_no_leak(self):
        self.need(REAL_KP)
        canon = self.load_canon()
        from src.data.vsl_gh_dataset import VSLGHContinuousDataset
        ds = {name: VSLGHContinuousDataset(canonical_json=REAL_CANON, keypoints_dir=REAL_KP, split=name,
                                           sentence_split=REAL_SPLIT) for name in ("train", "val", "test")}
        T, V, Tr = self.split.ids("test"), self.split.ids("val"), self.split.ids("train")
        sids = {k: {s["sentence_id"] for s in d.samples} for k, d in ds.items()}
        signers = {k: {s["signer_id"] for s in d.samples} for k, d in ds.items()}
        self.assertTrue(sids["train"].isdisjoint(T), sorted(sids["train"] & T))
        self.assertTrue(sids["val"].isdisjoint(T), sorted(sids["val"] & T))
        self.assertTrue(sids["train"].isdisjoint(V), sorted(sids["train"] & V))
        self.assertEqual(sids["train"], Tr)
        self.assertEqual(sids["val"], V)
        self.assertEqual(sids["test"], T)
        self.assertTrue(signers["train"] <= {"S01", "S02", "S03", "S04"})
        self.assertEqual(signers["val"], {"S05"})
        self.assertEqual(signers["test"], {"S06"})
        self.assertEqual(len(ds["test"]), 30)
        self.assertEqual(len(ds["val"]), 30)
        # independent recount from the raw canonical file
        self.assertEqual(len(ds["train"]), sum(1 for s in canon if s["signer_id"] in {"S01", "S02", "S03", "S04"}
                                               and s["sentence_id"] in Tr))
        # the default (train-only) vocabulary never contains a gloss seen only outside the CSLR train samples
        train_glosses = SS.collect_glosses(ds["train"].samples)
        self.assertEqual(set(ds["val"].vocab.gloss_to_id) - {"<blank>", "<unk>"}, train_glosses - {"<blank>", "<unk>"})

    def test_vit5_stage2_dataset_no_leak(self):
        self.need(REAL_CANON)
        from src.translation.dataset import VSLGHTextDataset
        ds = {name: VSLGHTextDataset(canonical_json=REAL_CANON, split=name, sentence_split=REAL_SPLIT)
              for name in ("train", "val", "test")}
        sids = {k: [s["sentence_id"] for s in d.samples] for k, d in ds.items()}
        self.assertTrue(set(sids["train"]).isdisjoint(set(self.split.heldout_ids())))
        self.assertEqual(sids["train"], list(self.split.train_ids))
        self.assertEqual(sids["val"], list(self.split.val_ids))
        self.assertEqual(sids["test"], list(self.split.test_ids))
        self.assertEqual((len(sids["train"]), len(sids["val"])), (240, 30))

    def test_vit5_stage1_clean10k_no_heldout_match(self):
        self.need(REAL_CLEAN10K)
        canon = self.load_canon()
        from src.translation.dataset import Clean10kDataset
        heldout = SS.heldout_texts(canon, self.split.heldout_ids())
        for name in ("train", "val"):
            plain = Clean10kDataset(jsonl_path=REAL_CLEAN10K, split=name)
            ds = Clean10kDataset(jsonl_path=REAL_CLEAN10K, split=name, exclude_heldout=heldout)
            for item in ds:
                hit, reason = SS.match_heldout(item["source"], item["target"], heldout)
                self.assertFalse(hit, (item["id"], reason))
            self.assertEqual(sorted([s["id"] for s in ds.samples] + ds.excluded_ids), sorted(s["id"] for s in plain.samples))


if __name__ == "__main__":
    unittest.main()
