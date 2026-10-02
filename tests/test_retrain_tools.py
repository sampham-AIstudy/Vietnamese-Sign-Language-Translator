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


# =====================================================================================================================
# B4c [plan 13 LS1] — `--sentence-split` in train_cslr.py / train_translation_stage{1,2}.py (§3.4f).
# No training: train_cslr runs with total_epochs=0 (no epoch at all) on a tiny synthetic fixture (18 clips with random
# keypoint arrays — fixture data for the code path, not a dataset); the ViT5 scripts stop at the first DataLoader
# (tokenizer / model are fakes, nothing is downloaded). Without the option every path must behave as before.
# =====================================================================================================================

class _StopHere(Exception):
    pass


class TestB4cSentenceSplitTraining(_Scratch):
    @classmethod
    def setUpClass(cls):
        from src.data import sentence_split as SS
        import src.training.train_cslr as TC
        import train_translation_stage1 as S1
        import train_translation_stage2 as S2
        cls.SS, cls.TC, cls.S1, cls.S2 = SS, TC, S1, S2

    def setUp(self):
        super().setUp()
        SS = self.SS
        write_bytes(self.p("split.json"), SS.split_file_bytes(SS.make_split_dict(ss_canonical(), seed=42)))
        self.split_path = self.p("split.json")
        self.split = SS.load_sentence_split(self.split_path)
        self.tr_sid, self.va_sid, self.te_sid = self.split.train_ids[0], self.split.val_ids[0], "SENT271"
        # mini canonical: 3 sentences (one per split) x 6 signers x 1 repetition
        self.data_root = self.p("vsl_gh")
        items = []
        for sid in (self.tr_sid, self.va_sid, self.te_sid):
            for signer, sp in SS_SIGNERS.items():
                items.append({"id": f"{sid}_{signer}_R01_F", "sentence_id": sid, "signer_id": signer, "split": sp,
                              "gloss_sequence": [f"G{sid[4:]}", "CHUNG"], "translation": f"Câu {int(sid[4:])}."})
        self.items = items
        write_canonical(os.path.join(self.data_root, "dataset_canonical.json"), items)
        kp = os.path.join(self.data_root, "keypoints_frontal")
        os.makedirs(kp)
        import numpy as np
        rng = np.random.RandomState(0)
        for it in items:
            np.save(os.path.join(kp, it["id"] + ".npy"), rng.rand(24, 411).astype(np.float32))
        # vocabularies: train-only (sentence split) and full (old recipe)
        self.vocab_train = self.p("vocab_train.txt")
        tokens, _, _ = V.build_tokens_train_only(os.path.join(self.data_root, "dataset_canonical.json"),
                                                 self.split_path, "train")
        write_bytes(self.vocab_train, "".join(t + "\n" for t in tokens).encode("utf-8"))
        self.vocab_full = self.p("vocab_full.txt")
        full = V.build_tokens(os.path.join(self.data_root, "dataset_canonical.json"))
        write_bytes(self.vocab_full, "".join(t + "\n" for t in full).encode("utf-8"))

    # ---------------- CSLR ----------------
    def cslr_config(self, vocab, with_split):
        cfg = {"data_root": self.data_root, "vocab_path": vocab,
               "pretrained_backbone": self.p("no_backbone.pt"), "checkpoint_dir": self.p("ckpt"),
               "reports_dir": self.p("reports"), "batch_size": 2, "total_epochs": 0, "stage1_epochs": 0,
               "stage1_lr": 1e-3, "stage2_backbone_lr": 1e-4, "stage2_head_lr": 5e-4, "hidden_size": 16,
               "num_gru_layers": 1, "dropout": 0.0, "early_stopping_patience": 10, "seed": 42}
        if with_split:
            cfg.update(self.TC.sentence_split_config(self.split_path))
        return cfg

    def run_cslr(self, cfg):
        from unittest import mock
        made = []
        real = self.TC.VSLGHContinuousDataset

        def recording(*a, **k):
            ds = real(*a, **k)
            made.append((k.get("split"), k.get("sentence_split"), ds))
            return ds

        out = io.StringIO()
        with mock.patch.object(self.TC, "VSLGHContinuousDataset", recording), contextlib.redirect_stdout(out):
            summary = self.TC.train_cslr(cfg, skip_smoke_test=True)
        return summary, made, out.getvalue()

    def test_cslr_sentence_split_config(self):
        c = self.TC.sentence_split_config(self.split_path)
        self.assertEqual(c, {"sentence_split_path": self.split_path, "sentence_split_sha256": self.split.sha256})
        bad = self.p("bad_split.json")
        write_bytes(bad, b'{"version": "x"}')
        with self.assertRaises(ValueError):
            self.TC.sentence_split_config(bad)

    def test_cslr_default_unchanged(self):
        cfg = self.cslr_config(self.vocab_full, with_split=False)
        before = dict(cfg)
        summary, made, log = self.run_cslr(cfg)
        self.assertEqual(cfg, before)  # no key added to the config (saved inside checkpoints)
        self.assertEqual([(s, ss) for s, ss, _ in made], [("train", None), ("val", None), ("test", None)])
        self.assertEqual([len(ds) for _, _, ds in made], [12, 3, 3])  # old signer split, all 3 sentences
        self.assertEqual(log.count("PRIMARY TEST EVALUATION"), 1)
        self.assertNotIn("TEST DEFERRED", log)
        self.assertNotIn("LEAK CHECK", log)
        self.assertTrue(os.path.isfile(self.p("reports", "cslr_test_results.json")))
        self.assertFalse(os.path.exists(self.p("reports", "cslr_used_ids.json")))
        self.assertIn("test_s06", summary)
        self.assertNotIn("sentence_split_path", summary["config"])

    def test_cslr_sentence_split_defers_test_and_records_ids(self):
        cfg = self.cslr_config(self.vocab_train, with_split=True)
        summary, made, log = self.run_cslr(cfg)
        self.assertEqual([s for s, _, _ in made], ["train", "val"])  # the test dataset is never built
        tr, va = made[0][2], made[1][2]
        self.assertEqual({(x["signer_id"], x["sentence_id"]) for x in tr.samples},
                         {(s, self.tr_sid) for s in ("S01", "S02", "S03", "S04")})
        self.assertEqual({(x["signer_id"], x["sentence_id"]) for x in va.samples}, {("S05", self.va_sid)})
        self.assertEqual(log.count("PRIMARY TEST EVALUATION"), 0)
        self.assertEqual(log.count("TEST DEFERRED (sentence split v1): run scripts/eval_sentsplit.py once"), 1)
        self.assertEqual(log.count("LEAK CHECK OK"), 1)
        self.assertLess(log.index("LEAK CHECK OK"), log.index("CSLR TRAINING STARTED"))
        self.assertFalse(os.path.exists(self.p("reports", "cslr_test_results.json")))
        with open(self.p("reports", "cslr_used_ids.json"), encoding="utf-8") as f:
            used = json.load(f)
        self.assertEqual(used["sentence_split_sha256"], self.split.sha256)
        self.assertEqual(sorted((u["sample_id"], u["sentence_id"]) for u in used["train"]),
                         sorted((x["id"], x["sentence_id"]) for x in tr.samples))
        self.assertEqual([(u["sample_id"], u["sentence_id"]) for u in used["val"]], [(f"{self.va_sid}_S05_R01_F", self.va_sid)])
        self.assertIsNone(summary["test_s06"])
        self.assertTrue(summary["test_deferred"])
        self.assertEqual(summary["config"]["sentence_split_sha256"], self.split.sha256)
        self.assertEqual(summary["config"]["sentence_split_path"], self.split_path)

    def test_cslr_sentence_split_refuses_full_vocab(self):
        # the full vocabulary contains glosses of val/test sentences -> label space leak -> stop before training
        with self.assertRaises(RuntimeError) as cm:
            self.run_cslr(self.cslr_config(self.vocab_full, with_split=True))
        self.assertIn("LEAK CHECK FAILED", str(cm.exception))

    def test_cslr_sentence_split_sha_mismatch_refused(self):
        cfg = self.cslr_config(self.vocab_train, with_split=True)
        cfg["sentence_split_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.run_cslr(cfg)

    def test_cslr_smoke_test_filters_by_split(self):
        from unittest import mock
        seen = []

        def stop(ds, indices):
            seen.append(ds)
            raise _StopHere()

        import torch
        for split_arg, expect in ((self.split_path, {(s, self.tr_sid) for s in ("S01", "S02", "S03", "S04")}),
                                  (None, {(s, sid) for s in ("S01", "S02", "S03", "S04")
                                          for sid in (self.tr_sid, self.va_sid, self.te_sid)})):
            seen.clear()
            kw = {} if split_arg is None else {"sentence_split": split_arg}
            with mock.patch.object(self.TC, "Subset", stop), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(_StopHere):
                    self.TC.run_smoke_test(__import__("pathlib").Path(self.data_root),
                                           __import__("pathlib").Path(self.vocab_train),
                                           __import__("pathlib").Path(self.p("no_backbone.pt")),
                                           torch.device("cpu"), **kw)
            self.assertEqual({(x["signer_id"], x["sentence_id"]) for x in seen[0].samples}, expect)

    def test_cslr_cli_has_option(self):
        res = subprocess.run([sys.executable, os.path.join(ROOT, "src", "training", "train_cslr.py"), "--help"],
                             capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("--sentence-split", res.stdout)

    # ---------------- ViT5 ----------------
    def fake_hf(self):
        from unittest import mock

        class _Tok:
            pad_token_id = 0

        class _Model:
            def to(self, device):
                return self

        return (mock.patch.object(self.S1.AutoTokenizer, "from_pretrained", lambda *a, **k: _Tok()),
                mock.patch.object(self.S1.AutoModelForSeq2SeqLM, "from_pretrained", lambda *a, **k: _Model()))

    def write_10k(self):
        rows = [{"id": f"PAR_10K_{k:05d}", "vsl": f"TỪ{k} KHÁC{k} NỮA{k}", "vi": f"Một câu số {k} khác hẳn."}
                for k in range(1, 61)]
        v_num = int(self.va_sid[4:])
        rows += [{"id": "PAR_10K_09001", "vsl": "BẤT KỲ GÌ", "vi": "Câu 271."},             # L1 target, test sentence
                 {"id": "PAR_10K_09002", "vsl": "G271 CHUNG", "vi": "Hoàn toàn khác biệt nhé."},  # L1 source, test
                 {"id": "PAR_10K_09003", "vsl": "ĐIỀU KHÁC", "vi": f"câu {v_num}"}]          # L2 target, val sentence
        path = self.p("vie_vsl_10k_cleaned.jsonl")
        write_bytes(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8"))
        return path, {"PAR_10K_09001", "PAR_10K_09002", "PAR_10K_09003"}

    def run_stage(self, mod, fn, patch_ds_name, ds_kwargs, **kw):
        import functools
        from unittest import mock
        made = []

        def loader(ds, **k):
            made.append(ds)
            if len(made) == 2:
                raise _StopHere()
            return None

        p_tok, p_model = self.fake_hf()
        real = getattr(mod, patch_ds_name)
        out = io.StringIO()
        with p_tok, p_model, mock.patch.object(mod, "DataLoader", loader), \
                mock.patch.object(mod, patch_ds_name, functools.partial(real, **ds_kwargs)), \
                contextlib.redirect_stdout(out):
            with self.assertRaises(_StopHere):
                fn(checkpoint_dir=self.p("ckpt_vit5"), reports_dir=self.p("reports_vit5"), **kw)
        return made, out.getvalue()

    def test_stage1_default_unchanged(self):
        from src.translation.dataset import Clean10kDataset
        path, _ = self.write_10k()
        made, log = self.run_stage(self.S1, self.S1.train_stage1, "Clean10kDataset", {"jsonl_path": path})
        ref_tr = Clean10kDataset(jsonl_path=path, split="train", val_ratio=0.1, seed=42)
        ref_va = Clean10kDataset(jsonl_path=path, split="val", val_ratio=0.1, seed=42)
        self.assertEqual([s["id"] for s in made[0].samples], [s["id"] for s in ref_tr.samples])
        self.assertEqual([s["id"] for s in made[1].samples], [s["id"] for s in ref_va.samples])
        self.assertEqual(made[0].excluded, [])
        self.assertNotIn("LEAK CHECK", log)
        self.assertFalse(os.path.exists(self.p("reports_vit5", "vit5_stage1_used_ids.json")))

    def full_canonical(self):
        # held-out texts / sentence lists need every sentence of the split: full 300-sentence fixture
        canon = self.p("canonical_full", "dataset_canonical.json")
        write_canonical(canon, ss_canonical())
        return canon

    def test_stage1_sentence_split_excludes_and_records(self):
        path, leak_ids = self.write_10k()
        canon = self.full_canonical()
        made, log = self.run_stage(self.S1, self.S1.train_stage1, "Clean10kDataset", {"jsonl_path": path},
                                   sentence_split=self.split_path, canonical_json=canon)
        kept = {s["id"] for d in made for s in d.samples}
        excluded = {e["id"] for d in made for e in d.excluded}
        self.assertEqual(excluded, leak_ids)
        self.assertFalse(kept & leak_ids)
        self.assertEqual(len(kept) + len(excluded), 63)
        self.assertEqual(log.count("LEAK CHECK OK"), 1)
        with open(self.p("reports_vit5", "vit5_stage1_used_ids.json"), encoding="utf-8") as f:
            used = json.load(f)
        self.assertEqual(used["sentence_split_sha256"], self.split.sha256)
        self.assertEqual(used["train_ids"], [s["id"] for s in made[0].samples])
        self.assertEqual(used["val_ids"], [s["id"] for s in made[1].samples])
        self.assertEqual({e["id"] for e in used["excluded"]}, leak_ids)
        self.assertEqual(set(used["heldout_sentence_ids"]), set(self.split.val_ids) | set(self.split.test_ids))

    def test_stage1_canonical_json_requires_split(self):
        res = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "train_translation_stage1.py"),
                              "--canonical-json", "x.json"], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("--sentence-split", res.stderr)
        res = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "train_translation_stage1.py"), "--help"],
                             capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertIn("--sentence-split", res.stdout)

    def test_stage2_default_unchanged(self):
        canon = os.path.join(self.data_root, "dataset_canonical.json")  # the default path is patched to the fixture
        os.makedirs(self.p("stage1_model"))
        made, log = self.run_stage(self.S2, self.S2.train_stage2, "VSLGHTextDataset", {"canonical_json": canon},
                                   pretrained_stage1_path=self.p("stage1_model"))
        # old split by sentence index of the sorted ids: the 3 fixture sentences sorted -> train gets them all (< 240)
        from src.translation.dataset import VSLGHTextDataset
        self.assertEqual([s["id"] for s in made[0].samples],
                         [s["id"] for s in VSLGHTextDataset(canonical_json=canon, split="train").samples])
        self.assertEqual([s["id"] for s in made[1].samples],
                         [s["id"] for s in VSLGHTextDataset(canonical_json=canon, split="val").samples])
        self.assertNotIn("LEAK CHECK", log)
        self.assertFalse(os.path.exists(self.p("reports_vit5", "vit5_stage2_used_ids.json")))

    def test_stage2_sentence_split_uses_split_and_records(self):
        canon = self.full_canonical()
        os.makedirs(self.p("stage1_model"))
        made, log = self.run_stage(self.S2, self.S2.train_stage2, "VSLGHTextDataset", {"canonical_json": canon},
                                   pretrained_stage1_path=self.p("stage1_model"), sentence_split=self.split_path)
        self.assertEqual([s["sentence_id"] for s in made[0].samples], list(self.split.train_ids))
        self.assertEqual([s["sentence_id"] for s in made[1].samples], list(self.split.val_ids))
        self.assertEqual(log.count("LEAK CHECK OK"), 1)
        with open(self.p("reports_vit5", "vit5_stage2_used_ids.json"), encoding="utf-8") as f:
            used = json.load(f)
        self.assertEqual(used["train_sentence_ids"], list(self.split.train_ids))
        self.assertEqual(used["val_sentence_ids"], list(self.split.val_ids))
        self.assertFalse(set(used["train_sentence_ids"]) & (set(self.split.test_ids) | set(self.split.val_ids)))
        self.assertEqual(used["sentence_split_sha256"], self.split.sha256)

    def test_stage2_sentence_split_requires_stage1(self):
        canon = os.path.join(self.data_root, "dataset_canonical.json")
        from unittest import mock
        p_tok, p_model = self.fake_hf()
        with p_tok, p_model, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(FileNotFoundError):
                self.S2.train_stage2(pretrained_stage1_path=self.p("missing_stage1"), sentence_split=self.split_path,
                                     checkpoint_dir=self.p("ckpt_vit5"), reports_dir=self.p("reports_vit5"))

    def test_leak_report_function(self):
        SS = self.SS
        ok = SS.sample_leak_report(self.split, [{"sentence_id": self.tr_sid, "signer_id": "S01"}],
                                   [{"sentence_id": self.va_sid, "signer_id": "S05"}])
        self.assertEqual(ok["n_violations"], 0)
        self.assertTrue(SS.assert_no_leak(ok, "x").startswith("LEAK CHECK OK (x)"))
        bad = SS.sample_leak_report(self.split, [{"sentence_id": "SENT271", "signer_id": "S06"}],
                                    [{"sentence_id": self.tr_sid, "signer_id": "S05"}])
        self.assertGreater(bad["n_violations"], 0)
        self.assertEqual(bad["train_in_test"], ["SENT271"])
        self.assertEqual(bad["train_signers_outside"], ["S06"])
        self.assertEqual(bad["val_outside_val"], [self.tr_sid])
        with self.assertRaises(RuntimeError):
            SS.assert_no_leak(bad, "x")


# =====================================================================================================================
# B4d [plan 13 LS1] — scripts/eval_sentsplit.py (§3.12 + repro_v2 of §0.7) on SYNTHETIC predictions only.
# Never runs a model and never touches the real test set: CSLR / ViT5 steps are replaced by deterministic fakes, the
# fixture is the 300-sentence synthetic canonical above (its S06 x T clips are fixture rows, not data).
# =====================================================================================================================

def _row(sample_id, sid, ref, pred, S, D, I, src_a, src_b, reftext, out_a, out_b):
    return {"sample_id": sample_id, "sentence_id": sid, "signer_id": "S06", "ref_gloss_raw": list(ref),
            "ref_gloss": list(ref), "pred_gloss": list(pred), "S": S, "D": D, "I": I,
            "ref_gloss_vocab_encoded": list(ref), "n_ref_oov": 0, "mode_a_source": src_a, "mode_b_source": src_b,
            "reference": reftext, "mode_a_output": out_a, "mode_b_output": out_b}


class TestEvalSentsplit(_Scratch):
    @classmethod
    def setUpClass(cls):
        import eval_sentsplit as E
        cls.E = E

    def hand_rows(self):
        # hand-computed edit operations: sub (B->X), deletion (B), insertion (C)
        return [
            _row("SENT271_S06_R01_F", "SENT271", ["A", "B", "C"], ["A", "X", "C"], 1, 0, 0, "a b c", "a x c",
                 "tôi đi học.", "tôi đi học.", "tôi đi chơi."),
            _row("SENT272_S06_R01_F", "SENT272", ["A", "B", "C"], ["A", "C"], 0, 1, 0, "a b c", "a c",
                 "hôm nay trời đẹp.", "hôm nay trời đẹp.", "hôm nay đẹp."),
            _row("SENT273_S06_R01_F", "SENT273", ["A", "B"], ["A", "B", "C"], 0, 0, 1, "a b", "a b c",
                 "bạn khỏe không?", "bạn có khỏe không?", "bạn khỏe không?"),
        ]

    def proto(self, **boot):
        p = self.E.protocol_template("sentsplit_v1")
        p["bootstrap"].update(boot)
        return p

    # --- protocol / metrics ----------------------------------------------------------------------------------------
    def test_protocol_template_matches_plan_3_12(self):
        p = self.E.protocol_template("sentsplit_v1")
        self.assertEqual((p["bootstrap"]["rng"], p["bootstrap"]["seed"], p["bootstrap"]["n_resamples"]),
                         ("numpy.random.RandomState", 42, 1000))
        self.assertEqual((p["bootstrap"]["percentiles"], p["bootstrap"]["interpolation"], p["bootstrap"]["paired"]),
                         ([2.5, 97.5], "linear", True))
        self.assertEqual((p["bleu"]["tokenize"], p["bleu"]["smooth_method"], p["bleu"]["lowercase"]), ("13a", "exp", False))
        self.assertEqual(p["translation"]["generate"], {"num_beams": 4, "max_length": 64, "do_sample": False})
        self.assertEqual(p["translation"]["tokenizer"], {"max_length": 128, "padding": True, "truncation": True})
        self.assertEqual((p["cslr"]["device"], p["translation"]["device"], p["cslr"]["batch_size"]), ("cpu", "cpu", 8))
        self.assertEqual(p["test_set"]["expected_n"], 30)
        r = self.E.protocol_template("repro_v2")
        self.assertEqual((r["bootstrap"]["seed"], r["bootstrap"]["n_resamples"]), (42, 1000))
        with self.assertRaises(self.E.EvalError):
            self.E.protocol_template("nope")

    def test_check_protocol_refuses_unimplemented(self):
        p = self.proto()
        self.E.check_protocol(p, "sentsplit_v1")
        for sec, key, val in (("bootstrap", "rng", "numpy.random.default_rng"), ("bootstrap", "interpolation", "nearest"),
                              ("translation", "fallback_stage1", True), ("bootstrap", "paired", False)):
            q = json.loads(json.dumps(p))
            q[sec][key] = val
            with self.assertRaises(self.E.EvalError) as cm:
                self.E.check_protocol(q, "sentsplit_v1")
            self.assertEqual(cm.exception.code, 2)
        with self.assertRaises(self.E.EvalError):
            self.E.check_protocol(p, "repro_v2")

    def test_wer_sdi_hand_computed(self):
        m = self.E.metrics_sentsplit_v1(self.hand_rows(), self.proto(n_resamples=50))
        self.assertEqual((m["wer"]["S"], m["wer"]["D"], m["wer"]["I"], m["wer"]["N_ref"]), (1, 1, 1, 8))
        self.assertEqual(m["wer"]["wer"], 37.5)
        self.assertEqual(m["wer"]["wer_exact"], 37.5)
        self.assertEqual((m["wer"]["sub_rate"], m["wer"]["del_rate"], m["wer"]["ins_rate"]), (12.5, 12.5, 12.5))
        self.assertEqual(m["n_clips"], 3)
        bad = self.hand_rows()
        bad[0]["S"] = 0  # per-sample S/D/I must add up to compute_wer
        with self.assertRaises(self.E.EvalError):
            self.E.metrics_sentsplit_v1(bad, self.proto(n_resamples=5))

    def test_bleu_points_equal_sacrebleu_defaults(self):
        import sacrebleu
        rows = self.hand_rows()
        m = self.E.metrics_sentsplit_v1(rows, self.proto(n_resamples=5))
        refs = [r["reference"] for r in rows]
        self.assertEqual(m["bleu_mode_a"]["score"], sacrebleu.corpus_bleu([r["mode_a_output"] for r in rows], [refs]).score)
        self.assertEqual(m["bleu_mode_b"]["score"], sacrebleu.corpus_bleu([r["mode_b_output"] for r in rows], [refs]).score)
        self.assertIn("tok:13a", m["bleu_mode_a"]["signature"])
        self.assertIn("smooth:exp", m["bleu_mode_a"]["signature"])
        self.assertAlmostEqual(m["delta"]["score"], m["bleu_mode_a"]["score"] - m["bleu_mode_b"]["score"])

    def test_paired_bootstrap_deterministic_and_reads_seed(self):
        import numpy as np
        rows = self.hand_rows()
        a = self.E.metrics_sentsplit_v1(rows, self.proto(n_resamples=40, seed=42))
        b = self.E.metrics_sentsplit_v1(rows, self.proto(n_resamples=40, seed=42))
        c = self.E.metrics_sentsplit_v1(rows, self.proto(n_resamples=40, seed=7))
        self.assertEqual(a, b)
        self.assertEqual(c["bootstrap"]["seed"], 7)
        self.assertEqual(c["bootstrap"]["n_resamples"], 40)
        # paired: ONE RandomState(seed) stream, the same idx per resample for WER and both BLEU scores; reproduced
        # here independently for seed 42 and seed 7 (the seed / B are read from the protocol)
        import sacrebleu
        S = np.array([1, 0, 0]); D = np.array([0, 1, 0]); I = np.array([0, 0, 1]); N = np.array([3, 3, 2])
        refs = [r["reference"] for r in rows]
        ha = [r["mode_a_output"] for r in rows]
        hb = [r["mode_b_output"] for r in rows]
        for seed, m in ((42, a), (7, c)):
            rng = np.random.RandomState(seed)
            w, ba, dl = [], [], []
            for _ in range(40):
                idx = rng.choice(3, 3, replace=True)
                w.append((S[idx].sum() + D[idx].sum() + I[idx].sum()) / N[idx].sum() * 100.0)
                rr = [refs[i] for i in idx]
                sa = sacrebleu.corpus_bleu([ha[i] for i in idx], [rr]).score
                sb = sacrebleu.corpus_bleu([hb[i] for i in idx], [rr]).score
                ba.append(sa)
                dl.append(sa - sb)
            self.assertEqual(m["wer"]["ci_95"], [float(x) for x in np.percentile(w, [2.5, 97.5])])
            self.assertEqual(m["bleu_mode_a"]["ci_95"], [float(x) for x in np.percentile(ba, [2.5, 97.5])])
            self.assertEqual(m["delta"]["ci_95"], [float(x) for x in np.percentile(dl, [2.5, 97.5])])
        d = self.E.metrics_sentsplit_v1(rows, self.proto(n_resamples=0 + 7, seed=42))
        self.assertEqual(d["bootstrap"]["n_resamples"], 7)

    def test_repro_v2_reproduces_old_audit_algorithm(self):
        # Run the ORIGINAL code of reports/audit_round2/run_v2_cslr_bootstrap.py (bootstrap + WER part, read from the
        # file) on synthetic predictions and compare with metrics_repro_v2.
        import numpy as np
        import sacrebleu
        with open(os.path.join(ROOT, "reports", "audit_round2", "run_v2_cslr_bootstrap.py"), encoding="utf-8") as f:
            src = f.read()
        start = src.index("# 2. Bootstrap 95% CI")
        end = src.index("v2_results = {")
        rng = np.random.RandomState(3)
        words = ["TÔI", "ĐI", "HỌC", "BẠN", "ĂN", "CƠM", "NHÀ"]
        texts = ["tôi đi học.", "bạn ăn cơm chưa?", "nhà tôi ở xa.", "hôm nay trời đẹp.", "tôi không biết."]
        s06 = []
        for i in range(1, 41):
            sid = f"SENT{(i * 7) % 300 + 1:03d}" if i <= 25 else f"SENT{270 + i - 25:03d}"
            ref = [words[k] for k in rng.randint(0, 7, size=rng.randint(2, 6))]
            pred = [w if rng.rand() > 0.3 else words[rng.randint(0, 7)] for w in ref][: max(1, len(ref) - rng.randint(0, 2))]
            s06.append({"sample_id": f"{sid}_S06_R01_F", "sentence_id": sid, "ref_gloss_list": ref, "pred_gloss_list": pred,
                        "translation": texts[i % 5]})
        unseen = [s for s in s06 if s["sentence_id"] >= "SENT271"]
        refs = [t.lower() for t in (s["translation"] for s in unseen)]
        a_preds = [texts[(k + 1) % 5] if k % 3 == 0 else refs[k] for k in range(len(unseen))]
        b_preds = [texts[(k + 2) % 5] if k % 2 == 0 else refs[k] for k in range(len(unseen))]
        g = {"np": np, "s06_samples": s06, "unseen_samples": unseen, "unseen_refs": refs, "mode_a_preds": a_preds,
             "mode_b_preds": b_preds}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(src[start:end], "run_v2_cslr_bootstrap.py", "exec"), g)
        rows = []
        k = 0
        for s in s06:
            r = {"sample_id": s["sample_id"], "sentence_id": s["sentence_id"], "ref_gloss_raw": s["ref_gloss_list"],
                 "pred_gloss": s["pred_gloss_list"]}
            if s["sentence_id"] >= "SENT271":
                r.update({"reference": refs[k], "mode_a_output": a_preds[k], "mode_b_output": b_preds[k]})
                k += 1
            rows.append(r)
        p = self.E.protocol_template("repro_v2")
        m = self.E.metrics_repro_v2(rows, p)
        self.assertEqual(m["n_unseen"], 15)
        self.assertEqual(m["bleu_mode_a"]["ci_95"], [float(x) for x in g["ci_a"]])
        self.assertEqual(m["bleu_mode_b"]["ci_95"], [float(x) for x in g["ci_b"]])
        self.assertEqual(m["delta"]["ci_95"], [float(x) for x in g["ci_diff"]])
        self.assertEqual(m["wer_300"]["score"], float(g["base_wer"]))
        self.assertEqual(m["wer_300"]["ci_95"], [float(x) for x in g["ci_wer"]])
        self.assertEqual(m["bleu_mode_a"]["score"], sacrebleu.corpus_bleu(a_preds, [refs]).score)

    # --- full run with fakes -----------------------------------------------------------------------------------------
    def build_inputs(self, protocol_overrides=None):
        import numpy as np
        import torch
        from src.data import sentence_split as SS
        E = self.E
        items = ss_canonical()
        canon = self.p("data", "dataset_canonical.json")
        write_canonical(canon, items)
        split_path = self.p("split.json")
        write_bytes(split_path, SS.split_file_bytes(SS.make_split_dict(items, seed=42)))
        split = SS.load_sentence_split(split_path)
        kp = self.p("data", "keypoints_frontal")
        os.makedirs(kp)
        for it in items:
            if it["signer_id"] == "S06" and it["sentence_id"] in split.test_ids:
                np.save(os.path.join(kp, it["id"] + ".npy"), np.zeros((4, 411), dtype=np.float32))
        tokens, _, _ = V.build_tokens_train_only(canon, split_path, "train")
        vocab = self.p("vocab.txt")
        write_bytes(vocab, "".join(t + "\n" for t in tokens).encode("utf-8"))
        with open(vocab, "rb") as f:
            vocab_sha = sha(f.read())
        ckpt = self.p("ckpt", "cslr_best.pt")
        os.makedirs(os.path.dirname(ckpt))
        torch.save({"gloss_vocab_hash": vocab_sha[:16], "config": {"sentence_split_sha256": split.sha256}}, ckpt)
        vit5 = self.p("vit5", "best_model")
        write_bytes(os.path.join(vit5, "config.json"), b'{"fake": true}\n')
        write_bytes(os.path.join(vit5, "spiece.model"), b"\x00fake")
        with open(ckpt, "rb") as f:
            ckpt_sha = sha(f.read())
        files = [{"rel_path": "k2/cslr_best.pt", "sha256": ckpt_sha},
                 {"rel_path": "vit5_stage2/best_model/config.json", "sha256": sha(b'{"fake": true}\n')},
                 {"rel_path": "vit5_stage2/best_model/spiece.model", "sha256": sha(b"\x00fake")}]
        manifest = self.p("manifest.json")
        write_bytes(manifest, json.dumps({"files": files}).encode("utf-8"))
        proto = E.protocol_template("sentsplit_v1")
        proto["inputs"] = {"canonical_json": canon, "keypoints_dir": kp, "vocab": vocab, "cslr_checkpoint": ckpt,
                           "vit5_model_dir": vit5}
        proto["bootstrap"]["n_resamples"] = 30
        for (sec, key), val in (protocol_overrides or {}).items():
            proto[sec][key] = val
        prereg = {"evaluation_protocol": proto, "sentence_split": {"path": split_path, "sha256": split.sha256},
                  "libs_local": {"sacrebleu": E.pkg_version("sacrebleu"), "numpy": E.pkg_version("numpy")},
                  "vocab": {"sha256": vocab_sha},
                  "inputs": {"dataset_canonical": {"path": canon, "lf_sha256": D.lf_sha256(canon)}}}
        prereg_path = self.p("reports", "preregistration.json")
        write_bytes(prereg_path, json.dumps(prereg, ensure_ascii=False).encode("utf-8"))
        self.split, self.items = split, items
        return prereg_path, manifest, prereg

    def fake_heavy(self, git=None):
        from unittest import mock
        E = self.E
        calls = {"cslr": 0, "vit5": 0}

        def cslr(ckpt, vocab, dataset, protocol):
            calls["cslr"] += 1
            out = {}
            for k, s in enumerate(dataset.samples):
                ref = [g.strip() for g in s["gloss_sequence"] if g.strip()]
                out[s["id"]] = ref if k % 3 else ref[:1] + ["<unk>"]
            return out

        def vit5(model_dir, sources, protocol):
            calls["vit5"] += 1
            return [f"câu {src}." if i % 4 else "khác." for i, src in enumerate(sources)]

        state = git or {"head": "f" * 40, "code_dirty": False, "dirty_lines": [], "prereg_commit": "e" * 40,
                        "prereg_n_commits": 1, "prereg_is_ancestor": True}
        return calls, (mock.patch.object(E, "cslr_predict", cslr), mock.patch.object(E, "vit5_generate", vit5),
                       mock.patch.object(E, "git_state", lambda p: dict(state)))

    def run_main(self, argv, git=None):
        calls, patches = self.fake_heavy(git)
        out, err = io.StringIO(), io.StringIO()
        with patches[0], patches[1], patches[2], contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = self.E.main(argv)
        return rc, calls, out.getvalue(), err.getvalue()

    def argv(self, prereg, manifest, out):
        return ["--prereg", prereg, "--protocol", "sentsplit_v1", "--manifest", manifest, "--out", out]

    def test_full_run_once_json_contents(self):
        prereg, manifest, pr = self.build_inputs()
        out = self.p("reports", "eval", "test_eval.json")
        rc, calls, log, err = self.run_main(self.argv(prereg, manifest, out))
        self.assertEqual(rc, 0, err)
        self.assertEqual(calls, {"cslr": 1, "vit5": 2})
        self.assertEqual(log.count("EVAL RUN "), 1)
        with open(out, encoding="utf-8") as f:
            r = json.load(f)
        self.assertEqual(len(r["per_sample"]), 30)
        self.assertEqual(sorted(s["sentence_id"] for s in r["per_sample"]), list(self.split.test_ids))
        self.assertEqual({s["signer_id"] for s in r["per_sample"]}, {"S06"})
        self.assertEqual(r["protocol"], pr["evaluation_protocol"])
        for k in ("command", "git_commit", "code_dirty", "generated_at_utc", "python", "torch", "transformers",
                  "sacrebleu", "numpy", "device"):
            self.assertIn(k, r["generated_by"])
        self.assertIs(r["generated_by"]["code_dirty"], False)
        self.assertEqual(r["inputs"]["sentence_split_sha256"], self.split.sha256)
        self.assertEqual(set(r["inputs"]["vit5_model_files_sha256"]), {"config.json", "spiece.model"})
        m = r["metrics"]
        for k in ("S", "D", "I", "N_ref", "ci_95"):
            self.assertIn(k, m["wer"])
        for k in ("bleu_mode_a", "bleu_mode_b"):
            self.assertTrue({"score", "ci_95", "signature"} <= set(m[k]))
        self.assertTrue({"score", "ci_95", "ci_contains_zero"} <= set(m["delta"]))
        c = r["comparison_to_old"]
        self.assertTrue(c["items"]["bleu_mode_a"]["old_source"].startswith("reports/audit_round2/v2_cslr_reliability.json:"))
        self.assertIn("old_point_inside_new_ci", c["items"]["bleu_mode_b"])
        self.assertTrue(any("NOT chosen at random" in x for x in r["limitations"]))
        # second run into the same target -> 2, nothing recomputed
        rc2, calls2, _, _ = self.run_main(self.argv(prereg, manifest, out))
        self.assertEqual((rc2, calls2), (2, {"cslr": 0, "vit5": 0}))
        # recompute from the saved per-sample predictions -> identical metrics, no model call
        rc3, calls3, log3, _ = self.run_main(["--recompute-from", out, "--out", self.p("recompute.json")])
        self.assertEqual((rc3, calls3), (0, {"cslr": 0, "vit5": 0}))
        with open(self.p("recompute.json"), encoding="utf-8") as f:
            rr = json.load(f)
        self.assertTrue(rr["identical"])
        self.assertEqual(rr["metrics"], r["metrics"])
        # tampered per-sample -> recompute differs -> 3
        r["per_sample"][0]["mode_b_output"] = "hoàn toàn khác."
        tampered = self.p("tampered.json")
        write_bytes(tampered, json.dumps(r, ensure_ascii=False).encode("utf-8"))
        rc4, _, _, _ = self.run_main(["--recompute-from", tampered, "--out", self.p("recompute2.json")])
        self.assertEqual(rc4, 3)

    def test_refusals_before_any_model_call(self):
        prereg, manifest, pr = self.build_inputs()
        out = self.p("reports", "eval", "x.json")
        clean = {"head": "f" * 40, "code_dirty": False, "dirty_lines": [], "prereg_commit": "e" * 40,
                 "prereg_n_commits": 1, "prereg_is_ancestor": True}
        for git, why in (({**clean, "code_dirty": True, "dirty_lines": [" M src/x.py"]}, "dirty"),
                         ({**clean, "prereg_is_ancestor": False}, "not ancestor"),
                         ({**clean, "prereg_commit": None}, "not committed"),
                         ({**clean, "prereg_n_commits": 2}, "changed after commit")):
            rc, calls, _, _ = self.run_main(self.argv(prereg, manifest, out), git=git)
            self.assertEqual((rc, calls), (2, {"cslr": 0, "vit5": 0}), why)
        self.assertFalse(os.path.exists(out))
        # library version != preregistration -> 2
        bad = dict(pr, libs_local={"sacrebleu": "0.0.0", "numpy": pr["libs_local"]["numpy"]})
        p2 = self.p("reports", "prereg_badlib.json")
        write_bytes(p2, json.dumps(bad).encode("utf-8"))
        rc, calls, _, _ = self.run_main(self.argv(p2, manifest, out))
        self.assertEqual((rc, calls), (2, {"cslr": 0, "vit5": 0}))
        # vocab digest != preregistration -> 3
        bad = dict(pr, vocab={"sha256": "0" * 64})
        p3 = self.p("reports", "prereg_badvocab.json")
        write_bytes(p3, json.dumps(bad).encode("utf-8"))
        rc, calls, _, _ = self.run_main(self.argv(p3, manifest, out))
        self.assertEqual((rc, calls), (3, {"cslr": 0, "vit5": 0}))
        # model file not in the manifest -> 3
        m2 = self.p("manifest_other.json")
        write_bytes(m2, json.dumps({"files": [{"rel_path": "cslr_best.pt", "sha256": "0" * 64}]}).encode("utf-8"))
        rc, calls, _, _ = self.run_main(self.argv(prereg, m2, out))
        self.assertEqual((rc, calls), (3, {"cslr": 0, "vit5": 0}))
        # missing keypoints of one test clip -> 3 (never dropped)
        kp = pr["evaluation_protocol"]["inputs"]["keypoints_dir"]
        victim = sorted(os.listdir(kp))[0]
        os.rename(os.path.join(kp, victim), os.path.join(self.tmp, victim))
        rc, calls, _, err = self.run_main(self.argv(prereg, manifest, out))
        self.assertEqual((rc, calls), (3, {"cslr": 0, "vit5": 0}))
        self.assertIn("missing keypoints", err)
        self.assertFalse(os.path.exists(out))

    def test_cli_argument_rules(self):
        self.assertEqual(self.E.main(["--out", self.p("o.json")]), 2)
        self.assertEqual(self.E.main(["--prereg", "p.json", "--protocol", "sentsplit_v1", "--out", self.p("o.json")]), 2)
        self.assertEqual(self.E.main(["--recompute-from", "x.json", "--protocol", "sentsplit_v1",
                                      "--out", self.p("o.json")]), 2)

    def test_heavy_steps_run_on_tiny_random_models(self):
        # The real CSLR / ViT5 steps on TINY randomly initialised models built here (nothing downloaded, nothing
        # trained): catches wiring errors (model kwargs from the checkpoint config, collate, decode, generate) before
        # the one real run, where an error after the predictions would stop plan 13 (§7.2-7).
        import numpy as np
        import torch
        from tokenizers import Tokenizer, models, pre_tokenizers
        from transformers import PreTrainedTokenizerFast, T5Config, T5ForConditionalGeneration
        from src.data import sentence_split as SS
        from src.data.vsl_gh_dataset import VSLGHContinuousDataset, VSLGlossVocabulary
        from src.models.cslr_stgcn_bigru import STGCNBiGRU_CSLR
        items = ss_canonical()
        canon = self.p("data", "dataset_canonical.json")
        write_canonical(canon, items)
        split_path = self.p("split.json")
        write_bytes(split_path, SS.split_file_bytes(SS.make_split_dict(items, seed=42)))
        kp = self.p("data", "keypoints_frontal")
        os.makedirs(kp)
        rng = np.random.RandomState(0)
        test_items = [it for it in items if it["signer_id"] == "S06" and it["sentence_id"] >= "SENT271"]
        for it in test_items:
            np.save(os.path.join(kp, it["id"] + ".npy"), rng.rand(20, 411).astype(np.float32))
        tokens, _, _ = V.build_tokens_train_only(canon, split_path, "train")
        vocab = VSLGlossVocabulary(tokens=tokens)
        torch.manual_seed(0)
        cfg = {"hidden_size": 16, "num_gru_layers": 1, "dropout": 0.0}
        proto = self.E.protocol_template("sentsplit_v1")
        model = STGCNBiGRU_CSLR(num_classes=len(vocab), **proto["cslr"]["model"]["fixed"], **cfg)
        ckpt = {"config": cfg, "model_state_dict": model.state_dict()}
        ds = VSLGHContinuousDataset(canonical_json=canon, keypoints_dir=kp, split="test", vocabulary=vocab,
                                    sentence_split=split_path, **proto["cslr"]["dataset"])
        preds = self.E.cslr_predict(ckpt, vocab, ds, proto)
        self.assertEqual(sorted(preds), sorted(it["id"] for it in test_items))
        self.assertTrue(all(isinstance(g, str) for v in preds.values() for g in v))
        # tiny seq2seq: word-level fast tokenizer + 1-layer T5 with random weights
        words = ["<pad>", "</s>", "<unk>", "tôi", "đi", "học", "câu", "a", "b"]
        tk = Tokenizer(models.WordLevel({w: i for i, w in enumerate(words)}, unk_token="<unk>"))
        tk.pre_tokenizer = pre_tokenizers.Whitespace()
        fast = PreTrainedTokenizerFast(tokenizer_object=tk, pad_token="<pad>", eos_token="</s>", unk_token="<unk>")
        mdir = self.p("tiny_t5")
        fast.save_pretrained(mdir)
        t5 = T5ForConditionalGeneration(T5Config(vocab_size=len(words), d_model=8, d_ff=16, d_kv=4, num_layers=1,
                                                 num_heads=2, pad_token_id=0, eos_token_id=1,
                                                 decoder_start_token_id=0))
        t5.save_pretrained(mdir)
        outs = self.E.vit5_generate(mdir, ["tôi đi học", "a b", "câu"], proto)
        self.assertEqual(len(outs), 3)
        self.assertTrue(all(isinstance(o, str) for o in outs))

    def test_git_state_on_a_tracked_file(self):
        # read-only git queries on the committed split file (exactly one commit, ancestor of HEAD — plan 13 AC11/AC4)
        gs = self.E.git_state(os.path.join(ROOT, "configs", "vslgh_sentence_split_v1.json"))
        self.assertEqual(len(gs["head"]), 40)
        self.assertEqual(gs["prereg_n_commits"], 1)
        self.assertTrue(gs["prereg_is_ancestor"])
        self.assertIsInstance(gs["code_dirty"], bool)

    def test_no_hand_typed_old_numbers_in_source(self):
        with open(os.path.join(ROOT, "scripts", "eval_sentsplit.py"), encoding="utf-8") as f:
            src = f.read()
        body = src[src.index('"""', 3) + 3:]  # skip the module docstring
        for number in ("27.98", "23.18", "32.8", "17.6", "38.39", "13.62", "33.7"):
            self.assertNotIn(number, body, number)


if __name__ == "__main__":
    unittest.main()
