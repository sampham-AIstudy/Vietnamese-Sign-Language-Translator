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


if __name__ == "__main__":
    unittest.main()
