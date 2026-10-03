import ast
import random
import sys
import os
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.fingerspelling_compose import compose, LETTERS, TONE_MARKS, SPACE
from src.inference.level1_textbox import textbox_view
from src.inference.level1_core import Level1Speller, KEY_NAMES


class TestLevel1Textbox(unittest.TestCase):
    def test_tb1_invariants_random(self):
        rng = random.Random(0)
        vocab = list(LETTERS) + list(TONE_MARKS.keys()) + [SPACE]
        for _ in range(2000):
            length = rng.randint(0, 12)
            tokens = [rng.choice(vocab) for _ in range(length)]
            view = textbox_view(tokens)
            expected_text = compose(tokens)["text"]
            self.assertEqual(view["text"], expected_text)
            self.assertEqual(view["committed"] + view["active"], expected_text)
            self.assertEqual(view["cursor"], len(expected_text))

    def test_tb2_add_tone_and_backspace(self):
        tokens = ["b", "a", "dấu sắc"]
        view = textbox_view(tokens)
        self.assertEqual(view["active"], "bá")
        
        # Add dấu huyền
        tokens.append("dấu huyền")
        view = textbox_view(tokens)
        self.assertEqual(view["active"], "bà")
        self.assertEqual(view["active_tone"], "dấu huyền")
        self.assertEqual(view["tone_changes"], [{"from": "dấu sắc", "to": "dấu huyền"}])
        self.assertEqual(view["warnings"], [])
        
        # Backspace using speller
        sp = Level1Speller(0.5)
        for t in tokens:
            sp.on_result(1, {"status": "ok", "prediction": t, "confidence": 0.9, "candidates": [{"class": t}]})
        sp.key("backspace")
        view2 = textbox_view(sp.tokens)
        self.assertEqual(view2["active"], "bá")
        self.assertEqual(view2["tone_changes"], [])

    def test_tb3_space_separates_syllables(self):
        tokens = ["m", "e", "dấu nặng", " ", "c", "a"]
        view = textbox_view(tokens)
        self.assertEqual(view["committed"], "mẹ ")
        self.assertEqual(view["active"], "ca")
        
        tokens.append("dấu sắc")
        view = textbox_view(tokens)
        self.assertEqual(view["text"], "mẹ cá")

    def test_tb4_last_is_space(self):
        tokens = ["m", "e", "dấu nặng", " "]
        view = textbox_view(tokens)
        self.assertEqual(view["active"], "")
        self.assertEqual(view["committed"], view["text"])
        
        # Backspace
        sp = Level1Speller(0.5)
        for t in tokens:
            if t == " ":
                sp.key("space")
            else:
                sp.on_result(1, {"status": "ok", "prediction": t, "confidence": 0.9, "candidates": [{"class": t}]})
        sp.key("backspace")
        view2 = textbox_view(sp.tokens)
        self.assertEqual(view2["active"], "mẹ")

    def test_tb5_preview(self):
        tokens = ["c", "a", "dấu sắc"]
        rejected = {"prediction": "dấu huyền", "confidence": 0.4}
        view = textbox_view(tokens, rejected)
        self.assertEqual(view["preview"]["active_if_accepted"], "cà")
        self.assertEqual(view["text"], "cá")
        
        rejected2 = {"prediction": None, "confidence": None}
        view2 = textbox_view(tokens, rejected2)
        self.assertIsNone(view2["preview"])
        
        view3 = textbox_view(tokens, None)
        self.assertIsNone(view3["preview"])

    def test_tb6_warnings(self):
        tokens = ["b", "dấu sắc"]
        view = textbox_view(tokens)
        self.assertTrue(any(w["code"] == "tone_without_vowel" for w in view["warnings"]))
        
        tokens2 = ["a", "dấu sắc", "dấu huyền", " "]
        view2 = textbox_view(tokens2)
        self.assertFalse(any(w["code"] == "multiple_tones" for w in view2["warnings"]))
        self.assertEqual(view2["tone_changes"], [])

    def test_tb7_unknown_token(self):
        with self.assertRaises(ValueError):
            textbox_view(["c", "a", "unknown_token"])
        with self.assertRaises(ValueError):
            textbox_view(["c", "a"], {"prediction": "bad", "confidence": 0.9})

    def test_tb8_ast_imports(self):
        import_names = set()
        filepath = os.path.join(PROJECT_ROOT, "src", "inference", "level1_textbox.py")
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                import_names.add(node.module)
                
        forbidden = {"cv2", "PIL", "torch", "threading"}
        for f in forbidden:
            self.assertNotIn(f, import_names)
            for mod in import_names:
                self.assertFalse(mod and mod.startswith(f + "."))

        # Must only import from stdlib or src.inference.fingerspelling_compose
        allowed_prefixes = ("typing", "src.inference.fingerspelling_compose")
        for mod in import_names:
            if mod:
                self.assertTrue(mod in allowed_prefixes or mod.startswith("typing."), f"Unexpected import: {mod}")

if __name__ == "__main__":
    unittest.main()
