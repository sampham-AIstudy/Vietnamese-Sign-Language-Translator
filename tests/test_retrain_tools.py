"""Plan 13 (retrain missing checkpoints) — tools shared by the local machine and the Kaggle kernels.

B2 scope: `scripts/retrain_digest.py` (sha256 / LF-normalised sha256 / combined directory digest) and
`scripts/build_gloss_vocab_canonical.py` (CSLR gloss vocabulary written with LF line endings on every OS).
No network, no GPU, no real dataset: every fixture is a tiny hand-written JSON/text file inside a scratch directory
under `<repo>/_work/_test_tmp/` (kept inside the project on purpose — plan 13 forbids temp dirs outside it).
"""
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_gloss_vocab_canonical as V  # noqa: E402
import retrain_digest as D  # noqa: E402
from src.data.vsl_gh_dataset import VSLGlossVocabulary  # noqa: E402

VOCAB_SCRIPT = os.path.join(ROOT, "scripts", "build_gloss_vocab_canonical.py")
DIGEST_SCRIPT = os.path.join(ROOT, "scripts", "retrain_digest.py")
SCRATCH_PARENT = os.path.join(ROOT, "_work", "_test_tmp")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def write_bytes(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def write_canonical(path, items):
    write_bytes(path, json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"))


# Glosses chosen to exercise: duplicates across items, surrounding whitespace, empty/blank entries, Vietnamese
# diacritics (sorting is by code point), items without `gloss_sequence`, and special tokens appearing as glosses.
CANONICAL_ITEMS = [
    {"video_id": "SENT001_S01_R01", "gloss_sequence": ["TÔI", "ĐI", "HỌC"]},
    {"video_id": "SENT002_S01_R01", "gloss_sequence": [" HỌC ", "BẠN", "", "   "]},
    {"video_id": "SENT003_S02_R01", "gloss_sequence": ["ăn", "Ăn", "<unk>", "AN"]},
    {"video_id": "SENT004_S02_R01"},
    {"video_id": "SENT005_S03_R01", "gloss_sequence": ["<blank>", "TÔI", "z"]},
]
EXPECTED_TOKENS = ["<blank>", "<unk>"] + sorted({"TÔI", "ĐI", "HỌC", "BẠN", "ăn", "Ăn", "AN", "z"})


class _Scratch(unittest.TestCase):
    def setUp(self):
        os.makedirs(SCRATCH_PARENT, exist_ok=True)
        self._td = tempfile.TemporaryDirectory(dir=SCRATCH_PARENT, prefix="retrain_tools_")
        self.tmp = self._td.name

    def tearDown(self):
        self._td.cleanup()

    def p(self, *parts):
        return os.path.join(self.tmp, *parts)


class TestDigest(_Scratch):
    def test_sha256_file_matches_hashlib(self):
        data = b"abc\r\ndef\n" * 1000
        write_bytes(self.p("a.bin"), data)
        self.assertEqual(D.sha256_file(self.p("a.bin")), sha(data))

    def test_lf_sha256_equal_for_crlf_and_lf(self):
        lf = "dòng 1\ndòng 2\n".encode("utf-8")
        crlf = lf.replace(b"\n", b"\r\n")
        write_bytes(self.p("lf.txt"), lf)
        write_bytes(self.p("crlf.txt"), crlf)
        self.assertEqual(D.lf_sha256(self.p("lf.txt")), sha(lf))
        self.assertEqual(D.lf_sha256(self.p("crlf.txt")), sha(lf))
        self.assertNotEqual(D.sha256_file(self.p("crlf.txt")), D.sha256_file(self.p("lf.txt")))

    def test_lf_sha256_keeps_lone_cr(self):
        # Only the CRLF pair is normalised; a lone CR inside a line is real content and must change the digest.
        write_bytes(self.p("a.txt"), b"x\ry\n")
        write_bytes(self.p("b.txt"), b"xy\n")
        self.assertEqual(D.lf_sha256(self.p("a.txt")), sha(b"x\ry\n"))
        self.assertNotEqual(D.lf_sha256(self.p("a.txt")), D.lf_sha256(self.p("b.txt")))

    def test_dir_digest_formula_and_order_independent(self):
        files = {"b.npy": b"\x00\x01", "a.npy": b"hello", "c.npy": b""}
        for name in ("c.npy", "a.npy", "b.npy"):  # creation order != name order
            write_bytes(self.p("d", name), files[name])
        expected_text = "".join(f"{n} {sha(files[n])}\n" for n in sorted(files))
        digest, n = D.dir_digest(self.p("d"))
        self.assertEqual(n, 3)
        self.assertEqual(digest, sha(expected_text.encode("utf-8")))

    def test_dir_digest_pattern_and_non_recursive(self):
        write_bytes(self.p("d", "a.npy"), b"1")
        write_bytes(self.p("d", "b.txt"), b"2")
        write_bytes(self.p("d", "sub", "c.npy"), b"3")
        digest, n = D.dir_digest(self.p("d"), pattern="*.npy")
        self.assertEqual(n, 1)
        self.assertEqual(digest, sha(f"a.npy {sha(b'1')}\n".encode("utf-8")))

    def test_dir_digest_names_subset_and_missing(self):
        for name, data in (("1.npz", b"one"), ("2.npz", b"two"), ("3.npz", b"three")):
            write_bytes(self.p("d", name), data)
        digest, n = D.dir_digest(self.p("d"), names=["3.npz", "1.npz"])
        self.assertEqual(n, 2)
        self.assertEqual(digest, sha(f"1.npz {sha(b'one')}\n3.npz {sha(b'three')}\n".encode("utf-8")))
        with self.assertRaises(FileNotFoundError):
            D.dir_digest(self.p("d"), names=["1.npz", "9.npz"])

    def test_dir_digest_names_rejects_paths_and_duplicates(self):
        write_bytes(self.p("d", "1.npz"), b"one")
        with self.assertRaises(ValueError):
            D.dir_digest(self.p("d"), names=["../1.npz"])
        with self.assertRaises(ValueError):
            D.dir_digest(self.p("d"), names=["1.npz", "1.npz"])

    def test_cli_outputs_json(self):
        write_bytes(self.p("crlf.txt"), b"a\r\nb\r\n")
        write_bytes(self.p("d", "x.npy"), b"x")
        out = subprocess.run([sys.executable, DIGEST_SCRIPT, "lf-sha256", self.p("crlf.txt")],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["lf_sha256"], sha(b"a\nb\n"))
        out = subprocess.run([sys.executable, DIGEST_SCRIPT, "sha256", self.p("crlf.txt")],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["sha256"], sha(b"a\r\nb\r\n"))
        out = subprocess.run([sys.executable, DIGEST_SCRIPT, "dir", self.p("d"), "--pattern", "*.npy"],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(out.returncode, 0, out.stderr)
        res = json.loads(out.stdout)
        self.assertEqual(res["n_files"], 1)
        self.assertEqual(res["dir_digest"], sha(f"x.npy {sha(b'x')}\n".encode("utf-8")))


class TestBuildGlossVocab(_Scratch):
    def run_cli(self, canonical, out):
        return subprocess.run([sys.executable, VOCAB_SCRIPT, "--canonical", canonical, "--out", out],
                              capture_output=True, text=True, encoding="utf-8")

    def test_order_lf_and_exact_bytes(self):
        write_canonical(self.p("dataset_canonical.json"), CANONICAL_ITEMS)
        res = self.run_cli(self.p("dataset_canonical.json"), self.p("vocab", "gloss_vocab_canonical.txt"))
        self.assertEqual(res.returncode, 0, res.stderr)
        with open(self.p("vocab", "gloss_vocab_canonical.txt"), "rb") as f:
            data = f.read()
        self.assertNotIn(b"\r", data)
        self.assertTrue(data.endswith(b"\n"))
        self.assertEqual(data, "".join(t + "\n" for t in EXPECTED_TOKENS).encode("utf-8"))
        info = json.loads(res.stdout)
        self.assertEqual(info["n_tokens"], len(EXPECTED_TOKENS))
        self.assertEqual(info["sha256"], sha(data))
        self.assertEqual(info["vocab_hash16"], sha(data)[:16])

    def test_same_order_as_vsl_gloss_vocabulary(self):
        write_canonical(self.p("dataset_canonical.json"), CANONICAL_ITEMS)
        out = self.p("v.txt")
        self.assertEqual(self.run_cli(self.p("dataset_canonical.json"), out).returncode, 0)
        ref = VSLGlossVocabulary.from_canonical_dataset(self.p("dataset_canonical.json"))
        with open(out, "rb") as f:
            lines = f.read().decode("utf-8").split("\n")[:-1]
        self.assertEqual(lines, [ref.id_to_gloss[i] for i in range(len(ref))])
        # Round trip through the reader used by train_cslr.py / CSLRRecognizer gives the same id mapping.
        self.assertEqual(VSLGlossVocabulary.from_file(out).gloss_to_id, ref.gloss_to_id)

    def test_deterministic(self):
        write_canonical(self.p("dataset_canonical.json"), CANONICAL_ITEMS)
        self.assertEqual(self.run_cli(self.p("dataset_canonical.json"), self.p("v1.txt")).returncode, 0)
        self.assertEqual(self.run_cli(self.p("dataset_canonical.json"), self.p("v2.txt")).returncode, 0)
        with open(self.p("v1.txt"), "rb") as f1, open(self.p("v2.txt"), "rb") as f2:
            self.assertEqual(f1.read(), f2.read())

    def test_refuses_to_overwrite(self):
        write_canonical(self.p("dataset_canonical.json"), CANONICAL_ITEMS)
        write_bytes(self.p("v.txt"), b"KEEP ME\r\n")
        res = self.run_cli(self.p("dataset_canonical.json"), self.p("v.txt"))
        self.assertEqual(res.returncode, 2)
        with open(self.p("v.txt"), "rb") as f:
            self.assertEqual(f.read(), b"KEEP ME\r\n")

    def test_rejects_token_with_line_break_inside(self):
        items = [{"video_id": "x", "gloss_sequence": ["A\rB", "C"]}]
        write_canonical(self.p("dataset_canonical.json"), items)
        res = self.run_cli(self.p("dataset_canonical.json"), self.p("v.txt"))
        self.assertEqual(res.returncode, 3)
        self.assertFalse(os.path.exists(self.p("v.txt")))

    def test_missing_canonical(self):
        res = self.run_cli(self.p("nope.json"), self.p("v.txt"))
        self.assertEqual(res.returncode, 2)
        self.assertFalse(os.path.exists(self.p("v.txt")))

    def test_build_tokens_function(self):
        write_canonical(self.p("dataset_canonical.json"), CANONICAL_ITEMS)
        self.assertEqual(V.build_tokens(self.p("dataset_canonical.json")), EXPECTED_TOKENS)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = V.main(["--canonical", self.p("dataset_canonical.json"), "--out", self.p("m.txt")])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(buf.getvalue())["n_tokens"], len(EXPECTED_TOKENS))


# ---------------------------------------------------------------------------------------------------------------------
# B2c [plan 13 LS1] — train-only vocabulary: `--sentence-split <split.json> --split train`.
# Fixture: 300 synthetic sentences x the VSL-GH signer layout (S01-S04 train x3 reps, S05 val, S06 test).
# ---------------------------------------------------------------------------------------------------------------------
SS_SIGNERS = {"S01": "train", "S02": "train", "S03": "train", "S04": "train", "S05": "val", "S06": "test"}


def ss_canonical():
    items = []
    for i in range(1, 301):
        sid = f"SENT{i:03d}"
        for signer, split in SS_SIGNERS.items():
            for r in range(1, (3 if split == "train" else 1) + 1):
                glosses = [f"G{i:03d}", " CHUNG "]
                if i == 5 and signer == "S05":
                    glosses.append("CHỈ-S05")  # train sentence, but only the val SIGNER uses this gloss -> excluded
                if i == 5 and signer == "S02" and r == 2:
                    glosses.append("ĐÚNG-TRAIN")  # one train sample only -> kept
                items.append({"id": f"{sid}_{signer}_R{r:02d}_F", "sentence_id": sid, "signer_id": signer,
                              "split": split, "gloss_sequence": glosses, "translation": f"Câu {i}."})
    return items


class TestBuildGlossVocabSentenceSplit(_Scratch):
    def setUp(self):
        super().setUp()
        from src.data import sentence_split as SS
        self.SS = SS
        self.items = ss_canonical()
        write_canonical(self.p("dataset_canonical.json"), self.items)
        self.canon = self.p("dataset_canonical.json")
        write_bytes(self.p("split.json"), SS.split_file_bytes(SS.make_split_dict(self.items, seed=42)))
        self.split = SS.load_sentence_split(self.p("split.json"))
        assert "SENT005" in self.split.train_ids  # fixture assumption (seed 42 val set)

    def run_cli(self, *extra, out=None):
        out = out or self.p("vocab", "gloss_vocab_train.txt")
        return out, subprocess.run([sys.executable, VOCAB_SCRIPT, "--canonical", self.canon, "--out", out, *extra],
                                   capture_output=True, text=True, encoding="utf-8")

    def expected_train_tokens(self):
        train = {f"G{int(s[4:]):03d}" for s in self.split.train_ids} | {"CHUNG", "ĐÚNG-TRAIN"}
        return ["<blank>", "<unk>"] + sorted(train)

    def test_train_only_tokens_bytes_and_report(self):
        out, res = self.run_cli("--sentence-split", self.p("split.json"), "--split", "train")
        self.assertEqual(res.returncode, 0, res.stderr)
        with open(out, "rb") as f:
            data = f.read()
        expected = self.expected_train_tokens()
        self.assertEqual(data, "".join(t + "\n" for t in expected).encode("utf-8"))
        self.assertNotIn(b"\r", data)
        info = json.loads(res.stdout)
        self.assertEqual(info["n_tokens"], len(expected))
        self.assertEqual(info["sha256"], sha(data))
        self.assertEqual(info["vocab_hash16"], sha(data)[:16])
        self.assertEqual(info["split"], "train")
        self.assertEqual(info["sentence_split_sha256"], self.split.sha256)
        self.assertEqual(info["n_samples_selected"], 240 * 4 * 3)
        heldout = {f"G{int(s[4:]):03d}" for s in self.split.val_ids + self.split.test_ids}
        self.assertEqual(info["glosses_excluded"], sorted(heldout | {"CHỈ-S05"}))
        # glosses of val/test sentences never reach the vocabulary
        for g in heldout:
            self.assertNotIn(g, expected)
        # same order/ids as the reader used by train_cslr.py / CSLRRecognizer, and as the dataset default (B2b)
        self.assertEqual(VSLGlossVocabulary.from_file(out).gloss_to_id,
                         VSLGlossVocabulary(tokens=list(self.SS.collect_glosses(
                             self.SS.select_vslgh_samples(self.items, "train", self.split)))).gloss_to_id)

    def test_without_option_bytes_identical_to_unfiltered(self):
        out, res = self.run_cli()
        self.assertEqual(res.returncode, 0, res.stderr)
        ref = VSLGlossVocabulary.from_canonical_dataset(self.canon)
        with open(out, "rb") as f:
            self.assertEqual(f.read(), "".join(ref.id_to_gloss[i] + "\n" for i in range(len(ref))).encode("utf-8"))
        self.assertEqual(sorted(json.loads(res.stdout)), sorted(["out", "n_tokens", "sha256", "vocab_hash16",
                                                                   "canonical_lf_sha256"]))
        self.assertEqual(V.build_tokens(self.canon), [ref.id_to_gloss[i] for i in range(len(ref))])

    def test_train_only_deterministic(self):
        a, ra = self.run_cli("--sentence-split", self.p("split.json"), "--split", "train", out=self.p("a.txt"))
        b, rb = self.run_cli("--sentence-split", self.p("split.json"), "--split", "train", out=self.p("b.txt"))
        self.assertEqual((ra.returncode, rb.returncode), (0, 0))
        with open(a, "rb") as fa, open(b, "rb") as fb:
            self.assertEqual(fa.read(), fb.read())

    def test_option_errors(self):
        # --sentence-split without --split, --split without --sentence-split, unknown split name, invalid split file,
        # existing target: all exit 2 without writing.
        bad = self.SS.make_split_dict(self.items, seed=42)
        bad["train_ids"] = sorted(bad["train_ids"] + ["SENT271"])
        write_bytes(self.p("bad.json"), self.SS.split_file_bytes(bad))
        cases = [("--sentence-split", self.p("split.json")), ("--split", "train"),
                 ("--sentence-split", self.p("bad.json"), "--split", "train"),
                 ("--sentence-split", self.p("nope.json"), "--split", "train")]
        for extra in cases:
            out, res = self.run_cli(*extra, out=self.p("x.txt"))
            self.assertEqual(res.returncode, 2, (extra, res.stderr))
            self.assertFalse(os.path.exists(out), extra)
        out, res = self.run_cli("--sentence-split", self.p("split.json"), "--split", "test", out=self.p("x.txt"))
        self.assertNotEqual(res.returncode, 0)
        self.assertFalse(os.path.exists(out))
        write_bytes(self.p("keep.txt"), b"KEEP\n")
        out, res = self.run_cli("--sentence-split", self.p("split.json"), "--split", "train", out=self.p("keep.txt"))
        self.assertEqual(res.returncode, 2)
        with open(out, "rb") as f:
            self.assertEqual(f.read(), b"KEEP\n")

    def test_build_tokens_train_only_function(self):
        tokens, excluded, n_sel = V.build_tokens_train_only(self.canon, self.p("split.json"), "train")
        self.assertEqual(tokens, self.expected_train_tokens())
        self.assertIn("CHỈ-S05", excluded)
        self.assertEqual(n_sel, 240 * 4 * 3)


# =====================================================================================================================
# B4a — train.py --seed (plan 13 §3.4b): optional; absent (default) = exactly the old behaviour (no seeding call).
# The training itself is never run: get_vsl_dataloaders is replaced by a stub that stops main() right there.
# =====================================================================================================================

class _StopMain(Exception):
    pass


class TestTrainSeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import train as T  # repo-root train.py
        cls.T = T

    def run_main(self, argv):
        from unittest import mock
        calls = []

        def fake_loaders(*a, **k):
            calls.append(("loaders", None))
            raise _StopMain()

        def fake_seed(n):
            calls.append(("seed", n))

        with mock.patch.object(sys, "argv", ["train.py"] + argv), \
                mock.patch.object(self.T, "get_vsl_dataloaders", fake_loaders), \
                mock.patch.object(self.T, "set_seed", fake_seed), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(_StopMain):
                self.T.main()
        return calls

    def test_parse_default_none(self):
        from unittest import mock
        with mock.patch.object(sys, "argv", ["train.py"]):
            self.assertIsNone(self.T.parse_args().seed)

    def test_parse_seed(self):
        from unittest import mock
        with mock.patch.object(sys, "argv", ["train.py", "--seed", "42"]):
            self.assertEqual(self.T.parse_args().seed, 42)

    def test_old_options_unchanged(self):
        from unittest import mock
        with mock.patch.object(sys, "argv", ["train.py"]):
            a = vars(self.T.parse_args())
        self.assertEqual(a, {"config": "configs/experiments/baseline_bigru.yaml", "epochs": None, "batch_size": None,
                             "lr": None, "smoke_test": False, "max_batches": None, "seed": None})

    def test_main_without_seed_never_seeds(self):
        calls = self.run_main(["--config", "configs/experiments/stgcn.yaml"])
        self.assertEqual(calls, [("loaders", None)])

    def test_main_with_seed_seeds_before_dataloaders(self):
        calls = self.run_main(["--config", "configs/experiments/stgcn.yaml", "--seed", "42"])
        self.assertEqual(calls, [("seed", 42), ("loaders", None)])

    def test_set_seed_is_deterministic(self):
        import random
        import numpy as np
        import torch

        def draw():
            return (random.random(), float(np.random.rand()), float(torch.rand(1)))

        state = (random.getstate(), np.random.get_state(), torch.get_rng_state())
        try:
            self.T.set_seed(42)
            a = draw()
            self.T.set_seed(42)
            b = draw()
            self.T.set_seed(43)
            c = draw()
        finally:
            random.setstate(state[0])
            np.random.set_state(state[1])
            torch.set_rng_state(state[2])
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)


# =====================================================================================================================
# B4b — scripts/archive_retrain_kaggle.py (plan 13 §3.4c) with a FAKE Kaggle API (no network, no credentials).
# Scratch directories are under <repo>/_work/_test_tmp/ (inside _work/, as the script requires). No real symlink or
# junction is ever created (forbidden since the 30/9 incident): link detection is exercised by patching lstat.
# =====================================================================================================================

ARCH_DATASET = "owner1/vslt-retrain-test-fixture"


class _HttpError(Exception):
    def __init__(self, code):
        super().__init__(f"{code} Client Error")
        self.response = _Obj(status_code=code)


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _FakeKaggle:
    """Records every call. Before create the slug is absent (404) unless `exists`; after create it is `ready`."""

    def __init__(self, staging=None, exists=False, list_private=True, meta_private=True, download_tamper=None,
                 remote_override=None, download_source=None):
        self.calls, self.staging, self.exists, self.created = [], staging, exists, False
        self.list_private, self.meta_private = list_private, meta_private
        self.download_tamper, self.remote_override = download_tamper, remote_override
        self.download_source = download_source

    def __getattr__(self, name):  # any other API method (version / update / delete ...) is recorded and fails loudly
        if name.startswith("dataset_") or name.startswith("datasets_"):
            def forbidden(*a, **k):
                self.calls.append((name, k))
                raise AssertionError(f"forbidden Kaggle call {name}")
            return forbidden
        raise AttributeError(name)

    def dataset_status(self, dataset):
        self.calls.append(("dataset_status", dataset))
        if self.exists or self.created:
            return "ready"
        raise _HttpError(404)

    def dataset_create_new(self, **kw):
        self.calls.append(("dataset_create_new", kw))
        self.created = True
        return _Obj(status="ok", error=None, ref=ARCH_DATASET, url="u")

    def dataset_list(self, **kw):
        self.calls.append(("dataset_list", kw))
        if not (self.exists or self.created):
            return []
        return [_Obj(ref=ARCH_DATASET, is_private=self.list_private)]

    def dataset_metadata(self, dataset, path):
        self.calls.append(("dataset_metadata", dataset))
        p = os.path.join(path, "dataset-metadata.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"id": dataset, "info": {"isPrivate": self.meta_private}}, f)
        return p

    def _remote(self):
        if self.remote_override is not None:
            return dict(self.remote_override)
        return {n: os.path.getsize(os.path.join(self.staging, n)) for n in os.listdir(self.staging)
                if n != "dataset-metadata.json"}

    def dataset_list_files(self, dataset, page_token=None, page_size=20):
        self.calls.append(("dataset_list_files", page_token))
        return _Obj(files=[_Obj(name=n, total_bytes=s) for n, s in sorted(self._remote().items())],
                    next_page_token=None, error_message=None)

    def dataset_download_files(self, dataset, path=None, unzip=False, **kw):
        self.calls.append(("dataset_download_files", path, unzip))
        src = self.download_source or self.staging
        for n in os.listdir(src):
            if n != "dataset-metadata.json":
                with open(os.path.join(src, n), "rb") as fi, open(os.path.join(path, n), "wb") as fo:
                    fo.write(fi.read())
        if self.download_tamper:
            with open(os.path.join(path, self.download_tamper), "ab") as f:
                f.write(b"x")

    def names(self):
        return [c[0] for c in self.calls]


class TestArchiveRetrainKaggle(_Scratch):
    ALLOWED_CALLS = {"dataset_status", "dataset_create_new", "dataset_list", "dataset_metadata", "dataset_list_files",
                     "dataset_download_files"}

    @classmethod
    def setUpClass(cls):
        import archive_retrain_kaggle as R
        cls.R = R

    def setUp(self):
        super().setUp()
        self.src = self.p("src")
        self.files = {"cslr_best.pt": b"\x00\x01ckpt", "vit5_stage2/best_model/config.json": b'{"d_model": 8}\n',
                      "vit5_stage2/best_model/spiece.model": b"\x02spm", "logs/k2.log": b"epoch 1 loss 1.0\n"}
        for rel, data in self.files.items():
            write_bytes(os.path.join(self.src, *rel.split("/")), data)
        self.staging = self.p("staging_x")
        self.dl = self.p("verify_x")
        self.manifest = self.p("out", "x_manifest.json")

    def code(self, fn, *a, **kw):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                return fn(*a, **kw)
            except self.R.ArchiveError as e:
                return e.code

    def stage(self, src=None, staging=None, title="VSLT retrain test fixture", note="test fixture only"):
        return self.code(self.R.stage, src or self.src, staging or self.staging, ARCH_DATASET, title, note)

    def staged_ok(self):
        self.assertEqual(self.stage(), 0)
        return self.staging

    def verify(self, api, manifest=None):
        return self.code(self.R.verify, self.staging, ARCH_DATASET, self.dl, manifest or self.manifest, api,
                         ["verify", "--dataset", ARCH_DATASET], poll_s=0, timeout_s=0, sleep=lambda s: None,
                         clock=lambda: 0.0)

    # --- stage ---------------------------------------------------------------------------------------------------
    def test_stage_success_flat_names_sums_private_metadata(self):
        self.staged_ok()
        names = sorted(os.listdir(self.staging))
        expected = sorted([r.replace("/", "__") for r in self.files] + ["SHA256SUMS", "dataset-metadata.json"])
        self.assertEqual(names, expected)
        sums = self.R.parse_sums(os.path.join(self.staging, "SHA256SUMS"))
        self.assertEqual(sums, {r.replace("/", "__"): sha(d) for r, d in self.files.items()})
        with open(os.path.join(self.staging, "dataset-metadata.json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertIs(meta["isPrivate"], True)
        self.assertEqual(meta["id"], ARCH_DATASET)
        self.assertIn("test fixture only", meta["description"])
        self.assertEqual([n for n in os.listdir(self.tmp) if ".partial-" in n], [])

    def test_stage_outside_work_exit_2(self):
        outside = os.path.join(ROOT, "plan13_not_under_work_staging")
        self.assertEqual(self.stage(staging=outside), 2)
        self.assertFalse(os.path.exists(outside))
        self.assertEqual(self.stage(src=os.path.join(ROOT, "configs")), 2)
        self.assertEqual(self.code(self.R.require_under_work, self.R.WORK_ROOT, "x"), 2)  # _work itself is refused

    def test_stage_existing_staging_exit_2_untouched(self):
        self.staged_ok()
        before = sorted(os.listdir(self.staging))
        self.assertEqual(self.stage(), 2)
        self.assertEqual(sorted(os.listdir(self.staging)), before)

    def test_stage_link_or_reparse_point_exit_2(self):
        from unittest import mock
        real = self.R.is_link_or_reparse
        target = os.path.join(self.src, "logs", "k2.log")
        with mock.patch.object(self.R, "is_link_or_reparse",
                               lambda p: os.path.normcase(os.path.abspath(p)) == os.path.normcase(target) or real(p)):
            self.assertEqual(self.stage(), 2)
        self.assertFalse(os.path.exists(self.staging))
        target = os.path.join(self.src, "vit5_stage2")  # a directory junction
        with mock.patch.object(self.R, "is_link_or_reparse",
                               lambda p: os.path.normcase(os.path.abspath(p)) == os.path.normcase(target) or real(p)):
            self.assertEqual(self.stage(), 2)
        self.assertFalse(os.path.exists(self.staging))

    def test_is_link_or_reparse_detects_attribute(self):
        import stat as _stat
        from unittest import mock
        self.assertFalse(self.R.is_link_or_reparse(os.path.join(self.src, "cslr_best.pt")))
        fake = _Obj(st_mode=_stat.S_IFDIR, st_file_attributes=0x400)
        with mock.patch.object(self.R.os, "lstat", lambda p: fake):
            self.assertTrue(self.R.is_link_or_reparse("anything"))
        fake_link = _Obj(st_mode=_stat.S_IFLNK | 0o777)
        with mock.patch.object(self.R.os, "lstat", lambda p: fake_link):
            self.assertTrue(self.R.is_link_or_reparse("anything"))

    def test_stage_empty_dir_exit_2(self):
        os.makedirs(os.path.join(self.src, "empty_sub"))
        self.assertEqual(self.stage(), 2)
        self.assertFalse(os.path.exists(self.staging))

    def test_stage_double_underscore_and_reserved_names_exit_2(self):
        write_bytes(os.path.join(self.src, "a__b.txt"), b"x")
        self.assertEqual(self.stage(), 2)
        src2 = self.p("src2")
        write_bytes(os.path.join(src2, "SHA256SUMS"), b"x")
        self.assertEqual(self.stage(src=src2, staging=self.p("staging_y")), 2)

    def test_stage_secret_like_string_exit_2(self):
        write_bytes(os.path.join(self.src, "logs", "env.json"), b'{"KAGGLE_KEY": "redacted"}\n')
        self.assertEqual(self.stage(), 2)
        self.assertFalse(os.path.exists(self.staging))

    def test_stage_total_too_large_exit_2(self):
        from unittest import mock
        with mock.patch.object(self.R, "MAX_TOTAL_BYTES", 10):
            self.assertEqual(self.stage(), 2)
        self.assertFalse(os.path.exists(self.staging))
        self.assertEqual(self.R.MAX_TOTAL_BYTES, 3 * 1024 ** 3)

    def test_stage_bad_title_dataset_note_exit_2(self):
        self.assertEqual(self.stage(title="abc"), 2)
        self.assertEqual(self.stage(note="  "), 2)
        self.assertEqual(self.code(self.R.stage, self.src, self.staging, "no-slash", "VSLT retrain x", "n"), 2)

    # --- upload --------------------------------------------------------------------------------------------------
    def test_upload_creates_once_private_no_other_calls(self):
        self.staged_ok()
        api = _FakeKaggle(staging=self.staging)
        self.assertEqual(self.code(self.R.upload, self.staging, ARCH_DATASET, api), 0)
        creates = [c for c in api.calls if c[0] == "dataset_create_new"]
        self.assertEqual(len(creates), 1)
        kw = creates[0][1]
        self.assertIs(kw["public"], False)
        self.assertEqual(kw["dir_mode"], "skip")
        self.assertEqual(os.path.normcase(kw["folder"]), os.path.normcase(os.path.abspath(self.staging)))
        self.assertTrue(set(api.names()) <= self.ALLOWED_CALLS, api.names())

    def test_upload_existing_slug_exit_5_no_create(self):
        self.staged_ok()
        api = _FakeKaggle(staging=self.staging, exists=True)
        self.assertEqual(self.code(self.R.upload, self.staging, ARCH_DATASET, api), 5)
        self.assertNotIn("dataset_create_new", api.names())

    def test_upload_staging_outside_work_or_modified_exit(self):
        api = _FakeKaggle()
        self.assertEqual(self.code(self.R.upload, os.path.join(ROOT, "plan13_x_staging"), ARCH_DATASET, api), 2)
        self.staged_ok()
        with open(os.path.join(self.staging, "cslr_best.pt"), "ab") as f:
            f.write(b"!")
        api = _FakeKaggle(staging=self.staging)
        self.assertEqual(self.code(self.R.upload, self.staging, ARCH_DATASET, api), 3)
        self.assertNotIn("dataset_create_new", api.names())

    def test_source_has_no_forbidden_calls(self):
        with open(os.path.join(ROOT, "scripts", "archive_retrain_kaggle.py"), encoding="utf-8") as f:
            src = f.read()
        for bad in ("public=True", '"--public"', "dataset_metadata_update", "dataset_delete", "dataset_create_version",
                    "metadata --update", "rmtree", "os.remove(", "os.unlink(", "os.symlink", "shutil.copy"):
            self.assertNotIn(bad, src, bad)
        self.assertIn("public=False", src)

    # --- verify --------------------------------------------------------------------------------------------------
    def uploaded(self, **kw):
        self.staged_ok()
        api = _FakeKaggle(staging=self.staging, **kw)
        self.assertEqual(self.code(self.R.upload, self.staging, ARCH_DATASET, api), 0)
        return api

    def test_verify_success_manifest(self):
        api = self.uploaded()
        self.assertEqual(self.verify(api), 0)
        with open(self.manifest, encoding="utf-8") as f:
            m = json.load(f)
        self.assertTrue({"script", "command", "git_commit", "code_dirty", "verified_at_utc"} <= set(m["generated_by"]))
        self.assertEqual(m["generated_by"]["script"], "scripts/archive_retrain_kaggle.py")
        self.assertIs(m["dataset"]["is_private"], True)
        self.assertEqual(m["dataset"]["is_private_sources"], {"dataset_list_mine": True, "dataset_metadata": True})
        self.assertEqual(m["verified"]["n_files"], len(self.files))
        self.assertEqual(sorted(f["rel_path"] for f in m["files"]), sorted(self.files))
        for f in m["files"]:
            self.assertEqual(f["sha256"], sha(self.files[f["rel_path"]]))
            self.assertEqual(f["sha256"], f["sha256_after_download"])
            self.assertEqual(f["archive_name"], f["rel_path"].replace("/", "__"))
            self.assertEqual(f["size_bytes"], len(self.files[f["rel_path"]]))
        self.assertTrue(set(api.names()) <= self.ALLOWED_CALLS, api.names())

    def test_verify_downloaded_sha_mismatch_exit_3_no_manifest(self):
        api = self.uploaded(download_tamper="cslr_best.pt")
        self.assertEqual(self.verify(api), 3)
        self.assertFalse(os.path.exists(self.manifest))

    def test_verify_remote_list_differs_exit_3(self):
        api = self.uploaded(remote_override={"cslr_best.pt": 6})
        self.assertEqual(self.verify(api), 3)
        self.assertFalse(os.path.exists(self.manifest))

    def test_verify_not_private_exit_4(self):
        api = self.uploaded(list_private=False)
        self.assertEqual(self.verify(api), 4)
        api2 = _FakeKaggle(staging=self.staging, exists=True, meta_private=None)
        self.assertEqual(self.verify(api2), 4)
        self.assertFalse(os.path.exists(self.manifest))

    def test_verify_manifest_out_misplaced_or_existing_exit_2(self):
        api = self.uploaded()
        self.assertEqual(self.verify(api, manifest=os.path.join(ROOT, "reports", "plan13_x_manifest.json")), 2)
        self.assertEqual(self.verify(api, manifest=os.path.join(ROOT, "reports", "retrain_2026-10-02", "x.json")), 2)
        self.assertEqual(self.verify(api, manifest=os.path.join(os.path.dirname(ROOT), "x_manifest.json")), 2)
        ok_in_repo = os.path.join(ROOT, "reports", "retrain_2026-10-02", "inputs_tier1_manifest.json")
        if not os.path.exists(ok_in_repo):
            self.assertEqual(os.path.normcase(self.R.check_manifest_out(ok_in_repo)), os.path.normcase(ok_in_repo))
        self.assertEqual(self.verify(api), 0)
        with open(self.manifest, "rb") as f:
            first = f.read()
        self.assertEqual(self.verify(api), 2)  # never overwritten
        with open(self.manifest, "rb") as f:
            self.assertEqual(f.read(), first)

    def test_verify_download_dir_outside_work_exit_2(self):
        api = self.uploaded()
        rc = self.code(self.R.verify, self.staging, ARCH_DATASET, os.path.join(ROOT, "plan13_x_dl"), self.manifest,
                       api, [], poll_s=0, timeout_s=0, sleep=lambda s: None, clock=lambda: 0.0)
        self.assertEqual(rc, 2)
        self.assertFalse(os.path.exists(os.path.join(ROOT, "plan13_x_dl")))

    # --- restore -------------------------------------------------------------------------------------------------
    def verified(self):
        api = self.uploaded()
        self.assertEqual(self.verify(api), 0)
        return api

    def restore(self, api, dest, manifest=None):
        return self.code(self.R.restore, manifest or self.manifest, self.p("restore_dl"), dest, api)

    def test_restore_writes_all_then_skips_identical(self):
        api = self.verified()
        dest = self.p("dest")
        self.assertEqual(self.restore(api, dest), 0)
        for rel, data in self.files.items():
            with open(os.path.join(dest, *rel.split("/")), "rb") as f:
                self.assertEqual(f.read(), data)
        self.assertEqual(self.restore(api, dest), 0)  # identical files: skipped, not rewritten

    def test_restore_never_overwrites_different_file(self):
        api = self.verified()
        dest = self.p("dest")
        write_bytes(os.path.join(dest, "logs", "k2.log"), b"LOCAL DIFFERENT\n")
        self.assertEqual(self.restore(api, dest), 3)
        with open(os.path.join(dest, "logs", "k2.log"), "rb") as f:
            self.assertEqual(f.read(), b"LOCAL DIFFERENT\n")
        self.assertFalse(os.path.exists(os.path.join(dest, "cslr_best.pt")))  # nothing written at all

    def test_restore_rejects_tampered_manifest_and_bad_download(self):
        api = self.verified()
        with open(self.manifest, encoding="utf-8") as f:
            m = json.load(f)
        bad = json.loads(json.dumps(m))
        bad["files"][0]["rel_path"] = "../escape.bin"
        bad_path = self.p("bad_manifest.json")
        write_bytes(bad_path, json.dumps(bad).encode("utf-8"))
        self.assertEqual(self.restore(api, self.p("dest")), 0)
        self.assertEqual(self.restore(api, self.p("dest2"), manifest=bad_path), 2)
        other = json.loads(json.dumps(m))
        other["generated_by"]["script"] = "scripts/archive_private_kaggle.py"
        other_path = self.p("other_manifest.json")
        write_bytes(other_path, json.dumps(other).encode("utf-8"))
        self.assertEqual(self.restore(api, self.p("dest3"), manifest=other_path), 2)
        api_t = _FakeKaggle(staging=self.staging, exists=True, download_tamper="cslr_best.pt")
        self.assertEqual(self.restore(api_t, self.p("dest4")), 3)
        self.assertFalse(os.path.exists(self.p("dest4", "cslr_best.pt")))

    def test_cli_main_exit_codes(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.R.main(["stage", "--src", self.src]), 2)  # missing required args
            self.assertEqual(self.R.main(["stage", "--src", self.src, "--staging", self.staging, "--dataset",
                                          ARCH_DATASET, "--title", "VSLT retrain test fixture",
                                          "--licence-note", "fixture"]), 0)
            self.assertEqual(self.R.main(["upload", "--staging", self.staging, "--dataset", ARCH_DATASET],
                                         api=_FakeKaggle(staging=self.staging, exists=True)), 5)


if __name__ == "__main__":
    unittest.main()
