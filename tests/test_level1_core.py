"""
Plan 15 AC-C (Level 1 core: src/inference/level1_core.py) and AC-T (src/inference/level1_timing.py).

C8 load_level1_config: missing key / missing source or reason / move_speed <= still_speed / word_gap_ms < hand_lost_ms
-> ValueError; the real configs/level1_realtime.json loads.
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.level1_core import CONFIG_SPEC, load_level1_config, validate_level1_config  # noqa: E402

CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json")


def _real_raw():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestConfigC8(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_cfg_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _write(self, raw, name="c.json"):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        return p

    def test_real_config_loads(self):
        cfg = load_level1_config(CONFIG_PATH)
        self.assertEqual(set(cfg["values"]), set(CONFIG_SPEC))
        self.assertEqual(len(cfg["sha256"]), 64)
        self.assertGreater(cfg["values"]["move_speed"], cfg["values"]["still_speed"])
        self.assertGreaterEqual(cfg["values"]["word_gap_ms"], cfg["values"]["hand_lost_ms"])
        for k in CONFIG_SPEC:
            self.assertTrue(cfg["raw"][k]["reason"].strip())

    def test_missing_key(self):
        for key in CONFIG_SPEC:
            raw = _real_raw()
            del raw[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                load_level1_config(self._write(raw))

    def test_missing_source_or_reason(self):
        for field in ("source", "reason"):
            for key in ("hold_ms", "accept_confidence", "camera_api"):
                raw = _real_raw()
                del raw[key][field]
                with self.subTest(field=field, key=key), self.assertRaises(ValueError):
                    validate_level1_config(raw)
        raw = _real_raw()
        raw["hold_ms"]["reason"] = "  "
        with self.assertRaises(ValueError):
            validate_level1_config(raw)
        raw = _real_raw()
        raw["hold_ms"]["source"] = "measured"
        with self.assertRaises(ValueError):
            validate_level1_config(raw)
        raw = _real_raw()
        raw["hold_ms"]["source"] = "calibrated: reports/x.json@abc123"
        self.assertEqual(validate_level1_config(raw)["hold_ms"], raw["hold_ms"]["value"])

    def test_move_not_above_still(self):
        raw = _real_raw()
        raw["move_speed"]["value"] = raw["still_speed"]["value"]
        with self.assertRaises(ValueError):
            validate_level1_config(raw)

    def test_word_gap_below_hand_lost(self):
        raw = _real_raw()
        raw["word_gap_ms"]["value"] = raw["hand_lost_ms"]["value"] - 1
        with self.assertRaises(ValueError):
            validate_level1_config(raw)

    def test_wrong_types(self):
        for key, bad in (("hold_ms", "400"), ("min_sign_frames", 2.5), ("accept_confidence", 1.5),
                         ("camera_api", "v4l"), ("font_paths", []), ("still_speed", True), ("top_k", 0)):
            raw = _real_raw()
            raw[key]["value"] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_level1_config(raw)
        raw = _real_raw()
        raw["unknown_key"] = copy.deepcopy(raw["hold_ms"])
        with self.assertRaises(ValueError):
            validate_level1_config(raw)

    def test_not_json(self):
        p = os.path.join(self.tmp, "bad.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write("{not json")
        with self.assertRaises(ValueError):
            load_level1_config(p)


if __name__ == "__main__":
    unittest.main()
