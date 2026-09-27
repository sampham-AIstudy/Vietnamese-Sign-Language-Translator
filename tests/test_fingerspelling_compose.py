"""
Plan 03 AC3 (+ AC4 prediction kind): composing Level 1 tokens into Vietnamese text.

Unit: src/inference/fingerspelling_compose.compose (AC3-a..c), label consistency (AC3-d).
Endpoint: POST /api/fingerspelling/compose (AC3-e).
"""
import os
import sys
import tempfile
import unicodedata
import unittest

import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient  # noqa: E402

import backend.main as api  # noqa: E402
from build_alphabet_tasks import ALPHABET_CLASSES  # noqa: E402
from src.inference.fingerspelling_compose import (  # noqa: E402
    LETTERS, SPACE, TONE_MARKS, compose, token_kind)

COMPOSE = "/api/fingerspelling/compose"
DEPLOYED_CKPT = os.path.join(PROJECT_ROOT, "checkpoints", "alphabet_best.pt")


def toks(spec):
    """'v i ê t dấu nặng ␣ n a m' -> ['v', 'i', 'ê', 't', 'dấu nặng', ' ', 'n', 'a', 'm']."""
    out, words = [], spec.split(" ")
    i = 0
    while i < len(words):
        w = words[i]
        if w == "dấu":
            out.append(f"dấu {words[i + 1]}")
            i += 2
            continue
        out.append(SPACE if w == "␣" else w)
        i += 1
    return out


REQUIRED_CASES = [  # AC3-a, verbatim from the plan
    ("v i ê t dấu nặng ␣ n a m", "việt nam"),
    ("n g ư ơ i dấu huyền", "người"),
    ("h o a dấu huyền", "hòa"),
    ("t h u y dấu hỏi", "thủy"),
    ("t o a n dấu sắc", "toán"),
    ("h o a n g dấu huyền", "hoàng"),
    ("t u â n dấu sắc", "tuấn"),
    ("q u a dấu hỏi", "quả"),
    ("q u y dấu sắc", "quý"),
    ("q u ô c dấu sắc", "quốc"),
    ("g i a dấu huyền", "già"),
    ("g i dấu huyền", "gì"),
    ("g i ê n g dấu sắc", "giếng"),
    ("n g o a i dấu huyền", "ngoài"),
    ("k h u y u dấu hỏi", "khuỷu"),
    ("c ư a dấu hỏi", "cửa"),
    ("c ư u dấu huyền", "cừu"),
    ("m u ô n dấu sắc", "muốn"),
    ("k h u y ê n dấu sắc", "khuyến"),
    ("x o ă n dấu sắc", "xoắn"),
    ("t h u ơ dấu hỏi", "thuở"),
    ("c u a dấu hỏi", "của"),
    ("y dấu sắc", "ý"),
    ("đ a dấu ngã", "đã"),
    ("t o dấu sắc a n", "toán"),
    ("m e", "me"),
]


def nfc(s):
    return unicodedata.normalize("NFC", s)


class TestComposeTable(unittest.TestCase):
    def test_tokenizer_helper(self):
        self.assertEqual(toks("v i ê t dấu nặng ␣ n a m"), ["v", "i", "ê", "t", "dấu nặng", " ", "n", "a", "m"])

    def test_required_cases(self):  # AC3-a
        for spec, expected in REQUIRED_CASES:
            with self.subTest(spec):
                out = compose(toks(spec))
                self.assertEqual(out["text"], nfc(expected))
                self.assertEqual(out["warnings"], [])

    def test_syllables(self):
        self.assertEqual(compose(toks("v i ê t dấu nặng ␣ n a m"))["syllables"], [nfc("việt"), "nam"])


class TestComposeWarnings(unittest.TestCase):  # AC3-b
    def test_tone_without_vowel(self):
        out = compose(["b", "dấu sắc"])
        self.assertEqual(out["text"], "b")
        self.assertEqual([(w["code"], w["token_index"]) for w in out["warnings"]], [("tone_without_vowel", 1)])

    def test_tone_without_vowel_in_second_syllable_reports_global_index(self):
        out = compose(["a", " ", "b", "c", "dấu hỏi"])
        self.assertEqual(out["text"], "a bc")
        self.assertEqual([(w["code"], w["token_index"]) for w in out["warnings"]], [("tone_without_vowel", 4)])

    def test_multiple_tones_uses_last(self):
        out = compose(["a", "dấu sắc", "dấu huyền"])
        self.assertEqual(out["text"], nfc("à"))
        self.assertEqual([(w["code"], w["token_index"]) for w in out["warnings"]], [("multiple_tones", 1)])

    def test_empty(self):
        self.assertEqual(compose([]), {"text": "", "syllables": [], "warnings": []})

    def test_spaces_kept_verbatim(self):
        out = compose(["a", " ", " ", "b"])
        self.assertEqual(out["text"], "a  b")
        self.assertEqual(out["syllables"], ["a", "b"])
        self.assertEqual(out["warnings"], [])


class TestComposeErrors(unittest.TestCase):  # AC3-c
    def test_unknown_token_raises(self):
        with self.assertRaises(ValueError) as cm:
            compose(["x1"])
        self.assertIn("tokens[0]", str(cm.exception))
        for bad in ["A", "", "dấu", None, 3, ["a"]]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                compose(["a", bad])

    def test_output_is_nfc(self):
        for spec, _ in REQUIRED_CASES:
            with self.subTest(spec):
                self.assertTrue(unicodedata.is_normalized("NFC", compose(toks(spec))["text"]))

    def test_nfd_tokens_are_accepted_and_output_nfc(self):
        decomposed = [unicodedata.normalize("NFD", t) for t in toks("t u â n dấu sắc")]
        out = compose(decomposed)
        self.assertEqual(out["text"], nfc("tuấn"))
        self.assertTrue(unicodedata.is_normalized("NFC", out["text"]))

    def test_token_kind(self):
        self.assertEqual({token_kind(c) for c in LETTERS}, {"letter"})
        self.assertEqual({token_kind(c) for c in TONE_MARKS}, {"tone"})
        self.assertEqual(token_kind(" "), "space")
        with self.assertRaises(ValueError):
            token_kind("x1")

    def test_module_has_no_torch_or_fastapi_import(self):
        import ast
        path = os.path.join(PROJECT_ROOT, "src", "inference", "fingerspelling_compose.py")
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertEqual(imported, {"unicodedata", "typing"})


class TestLabelConsistency(unittest.TestCase):  # AC3-d
    def test_letters_and_tones_equal_alphabet_classes(self):
        self.assertEqual(len(LETTERS), 29)
        self.assertEqual(len(TONE_MARKS), 5)
        self.assertEqual(set(LETTERS) | set(TONE_MARKS), set(ALPHABET_CLASSES))

    @unittest.skipUnless(os.path.exists(DEPLOYED_CKPT), f"missing file: {DEPLOYED_CKPT}")
    def test_letters_and_tones_equal_deployed_checkpoint_classes(self):
        ckpt = torch.load(DEPLOYED_CKPT, map_location="cpu", weights_only=False)
        self.assertEqual(set(LETTERS) | set(TONE_MARKS), set(ckpt["classes"]))


class TestComposeEndpoint(unittest.TestCase):  # AC3-e
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.client = TestClient(api.app)

    @classmethod
    def tearDownClass(cls):
        api.ALPHABET_CKPT = os.path.join(PROJECT_ROOT, "checkpoints", "alphabet_best.pt")
        api._alphabet_model, api._alphabet_meta = None, None
        cls.tmp.cleanup()

    def setUp(self):  # no checkpoint: /compose must not need the model
        api.ALPHABET_CKPT = os.path.join(self.tmp.name, "does_not_exist.pt")
        api._alphabet_model, api._alphabet_meta = None, None

    def test_compose_works_without_checkpoint(self):
        r = self.client.post(COMPOSE, json={"tokens": toks("v i ê t dấu nặng ␣ n a m")})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["text"], nfc("việt nam"))
        self.assertEqual(body["tone_style"], "traditional")
        self.assertEqual(body["warnings"], [])
        self.assertIsNone(api._alphabet_model)
        self.assertEqual(self.client.post(api.ALPHABET_SEQUENCE_ENDPOINT, json={
            "landmarks": [None], "handedness": [""], "frame_width": 1, "frame_height": 1}).status_code, 503)

    def test_warnings_in_response(self):
        body = self.client.post(COMPOSE, json={"tokens": ["b", "dấu sắc"]}).json()
        self.assertEqual(body["text"], "b")
        self.assertEqual(body["warnings"][0]["code"], "tone_without_vowel")
        self.assertEqual(body["warnings"][0]["token_index"], 1)

    def test_unknown_token_is_422_with_position(self):
        r = self.client.post(COMPOSE, json={"tokens": ["a", "b", "x1"]})
        self.assertEqual(r.status_code, 422)
        self.assertIn("tokens[2]", r.text)

    def test_length_limit(self):
        self.assertEqual(api.COMPOSE_MAX_TOKENS, 200)
        self.assertEqual(self.client.post(COMPOSE, json={"tokens": ["a"] * 201}).status_code, 422)
        r = self.client.post(COMPOSE, json={"tokens": ["a"] * 200})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["text"], "a" * 200)

    def test_wrong_types_are_422(self):
        for body in ({"tokens": "abc"}, {"tokens": [1, 2]}, {}, {"tokens": None}, ["a"]):
            with self.subTest(body=body):
                self.assertEqual(self.client.post(COMPOSE, json=body).status_code, 422)

    def test_empty_tokens(self):
        r = self.client.post(COMPOSE, json={"tokens": []})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["text"], "")


if __name__ == "__main__":
    unittest.main()
