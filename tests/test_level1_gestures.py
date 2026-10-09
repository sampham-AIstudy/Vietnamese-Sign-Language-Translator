"""
Plan 15 lần sửa 13 §3.2 / §9 AC-G1–G3: deliberate gestures (src/inference/level1_gestures.py, configs/level1_gestures.json).

AC-G1 loader: a missing / unknown key, a missing source or reason, source != design, a value <= 0, a ratio > 1, strokes < 1
      -> ValueError; the committed file loads (values = the design table of §3.2).
AC-G2 DeliberateSpaceGesture: open palm + still for hold - 1 frame -> 0; >= hold -> exactly 1; held on -> still 1; one bad
      frame in the middle -> still fires; two bad frames in a row -> the hold starts again; open palm with still=False -> 0;
      another pose for > rearm then open palm again -> fires a second time; losing the hand re-arms.
AC-G3 WaveBackspaceGesture: 1 large stroke -> 0 (the same frames through the old BackspaceGestureTracker -> 1: the
      difference is recorded in test_g3_single_large_stroke_*); 2 strokes >= A in the window -> 1; 2 strokes of 0.9 A -> 0;
      2 strokes spread over more than the window -> 0; vertical / horizontal > 0.5 -> 0; flat fraction 0.85 -> 0; waving on
      after a backspace does not fire again until the flat hand ends + cooldown; losing the hand in the middle -> counts
      again; the same frames scaled by 0.5 or mirrored in x -> same result.

Lần sửa 13d (docs/plans/15-lan-sua-13d.md §5, part G2a):
AC-D1 the flat fraction and the vertical / horizontal ratio are taken from the start of the first stroke, not on the whole
      buffer (non-flat or vertically offset still frames just before the strokes do not block; inside the strokes they do).
AC-D2 the space re-arm needs another pose for MORE than space_rearm_ms (exactly space_rearm_ms is not enough).
AC-D3 wave_min_strokes and space_dropout_frames are read from the values (changed values change the behaviour).
AC-D4 (P2) hand frames inside the wave cooldown are not buffered: strokes done inside the cooldown never fire.
AC-D5 (THẤP-2) a landmark frame with NaN / inf is "no hand" for both trackers; width / height must be finite and > 0.

Every hand and every frame sequence below is a chuỗi tạo có kiểm soát để kiểm logic (controlled sequence built to check the
logic): hand shapes are hand-placed 21-point templates checked against the real pose predicates of level1_core
(is_flat_hand_backspace / is_open_palm_space); they are not data and no number here is a measurement.
"""
import copy
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.level1_core import BackspaceGestureTracker, is_flat_hand_backspace, is_open_palm_space  # noqa: E402
from src.inference.level1_gestures import (  # noqa: E402
    GESTURE_SPEC, DeliberateSpaceGesture, GestureEngine, WaveBackspaceGesture, load_gesture_config,
    palm_centre, palm_len, validate_gesture_config)

CONFIG = os.path.join(PROJECT_ROOT, "configs", "level1_gestures.json")
MODULE = os.path.join(PROJECT_ROOT, "src", "inference", "level1_gestures.py")

# design table of plan 15 lần sửa 13 §3.2 (values set BEFORE any measurement; the gate of §3.3 may not move them)
DESIGN_TABLE = {
    "space_hold_ms": 600, "space_dropout_frames": 1, "space_rearm_ms": 300, "wave_window_ms": 1500,
    "wave_min_amplitude": 0.6, "wave_min_strokes": 2, "wave_max_vertical_ratio": 0.5, "wave_min_flat_fraction": 0.9,
    "wave_cooldown_ms": 1000, "flat_thumb_min_ratio": 0.5, "flat_thumb_max_spread": 1.05, "gesture_flash_ms": 600,
    "legacy_flick_cooldown_ms": 400, "legacy_flick_window_ms": 250, "legacy_flick_min_dx": 0.05,
    "legacy_flick_min_speed": 0.30, "legacy_flick_palm_ratio": 0.35, "legacy_flick_dx_over_dy": 1.1,
    "legacy_flick_min_dt_s": 0.04,
}
RATIO_KEYS = ("wave_max_vertical_ratio", "wave_min_flat_fraction")
INT_KEYS = ("space_dropout_frames", "wave_min_strokes")

DT = 25.0  # ms between two frames of the controlled sequences (40 frames per second)


# ---------------------------------------------------------------------------------------------- hand templates
def _finger(mcp, angle_deg, lengths=(0.4, 0.65, 0.85)):
    """Straight finger from its MCP at angle_deg from 'up' (image y grows downwards): pip, dip, tip."""
    a = math.radians(angle_deg)
    d = np.array([math.sin(a), -math.cos(a)])
    return [np.asarray(mcp) + l * d for l in lengths]


def _template(finger_angles, thumb):
    """21 points [21, 3] (z = 0), wrist at the origin, palm length |p9 - p0| = 1."""
    p = np.zeros((21, 3))
    mcps = {5: (-0.25, -0.95), 9: (0.0, -1.0), 13: (0.22, -0.93), 17: (0.42, -0.85)}
    for (mcp_idx, mcp), angle in zip(sorted(mcps.items()), finger_angles):
        p[mcp_idx, :2] = mcp
        for k, q in enumerate(_finger(mcp, angle)):
            p[mcp_idx + 1 + k, :2] = q
    for k, q in enumerate(thumb):
        p[1 + k, :2] = q
    return p


# 4 long fingers straight and together, thumb straight along the index finger
FLAT = _template((0, 0, 0, 0), ((-0.2, -0.3), (-0.4, -0.5), (-0.5, -0.7), (-0.55, -0.9)))
# 4 long fingers fanned out, thumb spread away from the palm
OPEN_PALM = _template((-25, -8, 8, 25), ((-0.25, -0.25), (-0.5, -0.4), (-0.75, -0.5), (-1.0, -0.6)))
# fingers curled back towards the wrist (neither pose)
CURLED = FLAT.copy()
for _mcp in (5, 9, 13, 17):
    CURLED[_mcp + 1:_mcp + 4, :2] = FLAT[_mcp, :2] + np.array([[0.05, 0.25], [0.08, 0.35], [0.1, 0.4]])

PALM = 0.2  # palm length of the hands of the sequences, in aspect-corrected units


def hand(template, cx, cy, scale=PALM):
    out = template * scale
    out[:, 0] += cx
    out[:, 1] += cy
    return out


def to_mediapipe(points, width, height):
    """Inverse of level1_segmenter.aspect_points: x and z divided by width / height."""
    raw = np.array(points, dtype=np.float64)
    raw[:, 0] /= width / height
    raw[:, 2] /= width / height
    return raw


def stroke_path(start, amps, frames_per_stroke, still_before=4, still_after=8):
    """x of the palm: still at start, then one linear stroke per signed amplitude (endpoints reached exactly), then still."""
    xs = [start] * still_before
    x = start
    for a in amps:
        for k in range(1, frames_per_stroke + 1):
            xs.append(x + a * k / frames_per_stroke)
        x += a
    return xs + [x] * still_after


def frames_from(xs, ys=None, flat=None, t0=0.0, template=FLAT):
    out = []
    for i, x in enumerate(xs):
        y = 0.5 if ys is None else ys[i]
        f = True if flat is None else flat[i]
        out.append((t0 + i * DT, hand(template, x, y), f))
    return out


def transform(frames, scale=1.0, flip=False):
    out = []
    for ts, p, f in frames:
        if p is not None:
            p = p * scale
            if flip:
                p[:, 0] = -p[:, 0]
        out.append((ts, p, f))
    return out


def run_wave(tracker, frames):
    return [i for i, (ts, p, f) in enumerate(frames) if tracker.update(ts, p, f)]


def load_values():
    return load_gesture_config(CONFIG)["values"]


class TemplatesAreThePoses(unittest.TestCase):
    """The hand templates really are the poses, judged by the real predicates of level1_core."""

    def test_templates(self):
        for scale in (1.0, PALM):
            self.assertTrue(is_flat_hand_backspace(hand(FLAT, 0.5, 0.5, scale)))
            self.assertFalse(is_open_palm_space(hand(FLAT, 0.5, 0.5, scale)))
            self.assertTrue(is_open_palm_space(hand(OPEN_PALM, 0.5, 0.5, scale)))
            self.assertFalse(is_flat_hand_backspace(hand(OPEN_PALM, 0.5, 0.5, scale)))
            self.assertFalse(is_open_palm_space(hand(CURLED, 0.5, 0.5, scale)))
            self.assertFalse(is_flat_hand_backspace(hand(CURLED, 0.5, 0.5, scale)))
        self.assertAlmostEqual(palm_len(hand(FLAT, 0.3, 0.4)), PALM)
        np.testing.assert_allclose(palm_centre(hand(FLAT, 0.3, 0.4)),
                                   np.mean(hand(FLAT, 0.3, 0.4)[[0, 5, 9, 13, 17]], axis=0))

    def test_flat_hand_thresholds_are_parameters_with_the_old_values(self):
        """G1 adds the two thresholds of is_flat_hand_backspace as parameters (the engine passes the config values);
        without them the result is the old one."""
        p = hand(FLAT, 0.5, 0.5)
        self.assertEqual(is_flat_hand_backspace(p), is_flat_hand_backspace(p, 0.5, 1.05))
        self.assertTrue(is_flat_hand_backspace(p, 0.5, 1.05))
        self.assertFalse(is_flat_hand_backspace(p, 0.5, 0.9))   # thumb tip to little MCP ~0.97 palm
        self.assertFalse(is_flat_hand_backspace(p, 1.2, 1.05))  # thumb tip to wrist ~1.05 palm


# ================================================================================================ AC-G1 loader
class TestLoaderAcG1(unittest.TestCase):
    def setUp(self):
        with open(CONFIG, "rb") as f:
            self.data = f.read()
        self.raw = json.loads(self.data.decode("utf-8"))
        self.tmp = tempfile.mkdtemp(prefix="l13_g1_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _load(self, raw, text=None):
        path = os.path.join(self.tmp, "g.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(raw) if text is None else text)
        return load_gesture_config(path)

    def _bad(self, raw, text=None):
        with self.assertRaises(ValueError):
            self._load(raw, text)
        if text is None:
            with self.assertRaises(ValueError):
                validate_gesture_config(raw)

    def test_committed_file_loads(self):
        cfg = load_gesture_config(CONFIG)
        self.assertEqual(set(cfg), {"values", "raw", "sha256", "path"})
        self.assertEqual(cfg["sha256"], hashlib.sha256(self.data).hexdigest())
        self.assertEqual(cfg["path"], CONFIG)
        self.assertEqual(cfg["raw"], self.raw)
        self.assertEqual(set(cfg["values"]), set(GESTURE_SPEC))
        self.assertEqual(cfg["values"], DESIGN_TABLE)
        for key in GESTURE_SPEC:
            self.assertEqual(self.raw[key]["source"], "design", key)
            self.assertTrue(self.raw[key]["reason"].strip(), key)

    def test_spec_is_the_design_table(self):
        self.assertEqual(set(GESTURE_SPEC), set(DESIGN_TABLE))

    def test_missing_key(self):
        for key in GESTURE_SPEC:
            raw = copy.deepcopy(self.raw)
            del raw[key]
            self._bad(raw)

    def test_unknown_key(self):
        raw = copy.deepcopy(self.raw)
        raw["space_hold"] = {"value": 600, "source": "design", "reason": "typo"}
        self._bad(raw)
        raw = copy.deepcopy(self.raw)
        raw["_note"] = "a comment key (leading underscore) is allowed, like configs/level1_realtime.json"
        self.assertEqual(self._load(raw)["values"], DESIGN_TABLE)

    def test_entry_fields(self):
        for key in GESTURE_SPEC:
            for mutate in (lambda e: e.pop("source"), lambda e: e.pop("reason"), lambda e: e.pop("value"),
                           lambda e: e.update(reason=""), lambda e: e.update(reason="   "), lambda e: e.update(reason=3),
                           lambda e: e.update(source="calibrated: x.json@abc1234"), lambda e: e.update(source="measured"),
                           lambda e: e.update(source="Design"), lambda e: e.update(source=None),
                           lambda e: e.update(extra="x")):
                raw = copy.deepcopy(self.raw)
                mutate(raw[key])
                self._bad(raw)
            raw = copy.deepcopy(self.raw)
            raw[key] = raw[key]["value"]  # bare value instead of {value, source, reason}
            self._bad(raw)

    def test_values_out_of_domain(self):
        for key in GESTURE_SPEC:
            for bad in (0, -1, -0.5, True, False, None, "600", [600], float("nan"), float("inf")):
                raw = copy.deepcopy(self.raw)
                raw[key]["value"] = bad
                self._bad(raw)

    def test_ratio_above_one(self):
        for key in RATIO_KEYS:
            for bad in (1.0001, 1.5, 2):
                raw = copy.deepcopy(self.raw)
                raw[key]["value"] = bad
                self._bad(raw)
            raw = copy.deepcopy(self.raw)
            raw[key]["value"] = 1
            self.assertEqual(self._load(raw)["values"][key], 1)

    def test_strokes_below_one_and_int_keys(self):
        for bad in (0, 0.5, -2):
            raw = copy.deepcopy(self.raw)
            raw["wave_min_strokes"]["value"] = bad
            self._bad(raw)
        for key in INT_KEYS:
            raw = copy.deepcopy(self.raw)
            raw[key]["value"] = 2.5
            self._bad(raw)

    def test_not_an_object_or_not_json(self):
        self._bad([1, 2, 3])
        self._bad(None, text="{not json")
        self._bad(None, text="")

    def test_no_default_values_in_code(self):
        """No design value lives in the module: every numeric literal is a landmark index or an array shape."""
        import ast
        with open(MODULE, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        nums = {n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)}
        self.assertLessEqual(nums, {0, 1, 2, 3, 5, 9, 13, 17, 21}, nums)

    def test_module_passes_the_source_guard(self):
        """Preview of AC-G5 (the file joins the guard list in G2): no finding of the main guard's rules."""
        from tests.test_backend_source_guard import ALL_RULES, _read, scan_source
        rel = "src/inference/level1_gestures.py"
        self.assertEqual(scan_source(_read(MODULE), rel, ALL_RULES), [])


# ================================================================================================ AC-G2 space
class TestDeliberateSpaceAcG2(unittest.TestCase):
    def setUp(self):
        self.v = load_values()
        self.hold = self.v["space_hold_ms"]
        self.rearm = self.v["space_rearm_ms"]
        self.dropout = self.v["space_dropout_frames"]
        self.k_hold = int(math.ceil(self.hold / DT))  # first frame index whose time since frame 0 is >= hold
        self.tr = DeliberateSpaceGesture.from_values(self.v)
        self.t = 0.0

    def feed(self, frames):
        """frames: list of (is_palm, has_hand, still), DT apart, time going on from the previous call -> indices (in
        this call) that fired."""
        fired = []
        for i, (palm, hand_, still) in enumerate(frames):
            if self.tr.update(self.t, palm, hand_, still):
                fired.append(i)
            self.t += DT
        return fired

    GOOD = (True, True, True)
    BAD = (False, True, True)       # hand there, not the open palm (one flickering MediaPipe frame)
    NOT_STILL = (True, True, False)
    OTHER = (False, True, True)
    NO_HAND = (False, False, True)

    def test_hold_minus_one_frame_then_hold(self):
        self.assertGreater(self.k_hold, 2)
        self.assertEqual(self.feed([self.GOOD] * self.k_hold), [])  # last frame at hold - DT
        self.assertTrue(self.tr.update(self.t, True, True, True))  # time since the first frame == hold
        self.assertEqual(self.tr.n_emits, 1)

    def test_exactly_one_while_held_on(self):
        fired = self.feed([self.GOOD] * (self.k_hold * 5))
        self.assertEqual(fired, [self.k_hold])
        self.assertEqual(self.tr.n_emits, 1)

    def test_held_ms_reports_the_hold(self):
        self.feed([self.GOOD] * 4)
        self.assertEqual(self.tr.held_ms, 3 * DT)
        self.feed([self.GOOD] * (self.k_hold + 1))
        self.assertEqual(self.tr.held_ms, 0.0)  # disarmed after the space

    def test_one_bad_frame_in_the_middle_still_fires(self):
        mid = self.k_hold // 2
        seq = [self.GOOD] * mid + [self.BAD] * self.dropout + [self.GOOD] * (self.k_hold * 2)
        self.assertEqual(self.feed(seq), [self.k_hold])

    def test_two_bad_frames_in_a_row_restart_the_hold(self):
        mid = self.k_hold // 2
        n_bad = self.dropout + 1
        seq = [self.GOOD] * mid + [self.BAD] * n_bad + [self.GOOD] * (self.k_hold * 2)
        self.assertEqual(self.feed(seq), [mid + n_bad + self.k_hold])

    def test_open_palm_not_still_never_fires(self):
        self.assertEqual(self.feed([self.NOT_STILL] * (self.k_hold * 5)), [])
        # alternating still / not still: never still for long enough
        self.tr = DeliberateSpaceGesture.from_values(self.v)
        self.assertEqual(self.feed([self.NOT_STILL, self.NOT_STILL, self.GOOD] * (self.k_hold * 2)), [])

    def test_other_pose_longer_than_rearm_then_open_palm_fires_again(self):
        k_rearm = int(math.floor(self.rearm / DT)) + 2  # other pose held strictly longer than rearm
        seq = [self.GOOD] * (self.k_hold + 3) + [self.OTHER] * k_rearm + [self.GOOD] * (self.k_hold + 3)
        fired = self.feed(seq)
        start2 = self.k_hold + 3 + k_rearm
        self.assertEqual(fired, [self.k_hold, start2 + self.k_hold])

    def test_other_pose_shorter_than_rearm_does_not_rearm(self):
        k_short = int(math.floor(self.rearm / DT))  # other pose spans (k_short - 1) * DT < rearm
        seq = [self.GOOD] * (self.k_hold + 3) + [self.OTHER] * k_short + [self.GOOD] * (self.k_hold * 3)
        self.assertEqual(self.feed(seq), [self.k_hold])

    def test_not_still_longer_than_rearm_also_rearms(self):
        k_rearm = int(math.floor(self.rearm / DT)) + 2
        seq = [self.GOOD] * (self.k_hold + 3) + [self.NOT_STILL] * k_rearm + [self.GOOD] * (self.k_hold + 3)
        self.assertEqual(len(self.feed(seq)), 2)

    def test_losing_the_hand_rearms(self):
        seq = [self.GOOD] * (self.k_hold + 3) + [self.NO_HAND] + [self.GOOD] * (self.k_hold + 3)
        self.assertEqual(self.feed(seq), [self.k_hold, self.k_hold + 4 + self.k_hold])

    def test_losing_the_hand_cancels_the_hold(self):
        mid = self.k_hold // 2
        seq = [self.GOOD] * mid + [self.NO_HAND] + [self.GOOD] * (self.k_hold * 2)
        self.assertEqual(self.feed(seq), [mid + 1 + self.k_hold])

    def test_bad_timestamp_and_bad_parameters(self):
        with self.assertRaises(ValueError):
            self.tr.update(float("nan"), True, True, True)
        for kwargs in ({"hold_ms": 0, "dropout_frames": 1, "rearm_ms": 300},
                       {"hold_ms": 600, "dropout_frames": 0, "rearm_ms": 300},
                       {"hold_ms": 600, "dropout_frames": 1, "rearm_ms": float("inf")}):
            with self.assertRaises(ValueError):
                DeliberateSpaceGesture(**kwargs)

    def test_reset(self):
        self.feed([self.GOOD] * (self.k_hold + 2))
        self.tr.reset()
        self.assertEqual(self.feed([self.GOOD] * (self.k_hold + 2)), [self.k_hold])


# ================================================================================================ AC-G3 wave
class TestWaveBackspaceAcG3(unittest.TestCase):
    def setUp(self):
        self.v = load_values()
        self.A = self.v["wave_min_amplitude"] * PALM  # stroke threshold for hands of palm length PALM
        self.window = self.v["wave_window_ms"]
        self.cooldown = self.v["wave_cooldown_ms"]
        self.fast = 12  # frames per stroke: 300 ms, inside the window

    def wave(self):
        return WaveBackspaceGesture.from_values(self.v)

    def both_ways(self, frames, expected):
        """Same result on the frames, on the frames scaled by 0.5 and on the frames mirrored in x."""
        for scale, flip in ((1.0, False), (0.5, False), (1.0, True), (0.5, True)):
            got = run_wave(self.wave(), transform(frames, scale, flip))
            self.assertEqual(got, expected, f"scale={scale} flip={flip}")
        return expected

    def two_strokes(self, amp, frames_per_stroke=None, ys=None, flat=None):
        xs = stroke_path(0.5, (amp, -amp), frames_per_stroke or self.fast)
        return frames_from(xs, ys=ys, flat=flat)

    def test_g3_single_large_stroke_no_backspace_old_tracker_one(self):
        xs = stroke_path(0.4, (3 * self.A,), 8, still_after=40)  # one 200 ms stroke, then still
        frames = frames_from(xs)
        self.both_ways(frames, [])
        # difference recorded (AC-G3): the old flick tracker (commit 7a267c7) fires once on the same frames
        old = BackspaceGestureTracker()
        n_old = sum(old.update(ts, p, f, has_hand=True) for ts, p, f in frames)
        self.assertEqual(n_old, 1)

    def test_two_strokes_above_threshold_in_window(self):
        fired = run_wave(self.wave(), self.two_strokes(1.1 * self.A))
        self.assertEqual(len(fired), 1)
        self.both_ways(self.two_strokes(1.1 * self.A), fired)

    def test_two_strokes_of_point_nine_threshold(self):
        self.both_ways(self.two_strokes(0.9 * self.A), [])
        # many of them do not add up either
        xs = stroke_path(0.5, (0.9 * self.A, -0.9 * self.A) * 4, self.fast)
        self.both_ways(frames_from(xs), [])

    def test_two_strokes_spread_over_more_than_the_window(self):
        slow = int(self.window / DT)  # one stroke takes the whole window
        xs = stroke_path(0.5, (1.2 * self.A, -1.2 * self.A) * 2, slow)
        self.both_ways(frames_from(xs), [])
        # the same strokes fast enough fire (the duration is what blocks)
        xs = stroke_path(0.5, (1.2 * self.A, -1.2 * self.A) * 2, self.fast)
        self.assertGreaterEqual(len(run_wave(self.wave(), frames_from(xs))), 1)

    def _diagonal(self, ratio):
        xs = stroke_path(0.5, (1.2 * self.A, -1.2 * self.A), self.fast)
        ys = [0.5 + ratio * (x - 0.5) for x in xs]
        return frames_from(xs, ys=ys)

    def test_vertical_over_horizontal_above_ratio(self):
        r = self.v["wave_max_vertical_ratio"]
        self.both_ways(self._diagonal(r + 0.1), [])
        self.both_ways(self._diagonal(1.0), [])
        fired = run_wave(self.wave(), self._diagonal(r - 0.1))
        self.assertEqual(len(fired), 1)
        self.both_ways(self._diagonal(r - 0.1), fired)

    def _flat_pattern(self, n, nonflat_mod):
        return [i % 20 not in nonflat_mod for i in range(n)]

    def test_flat_fraction_point_eight_five(self):
        n = len(stroke_path(0.5, (1.2 * self.A, -1.2 * self.A) * 3, self.fast))
        flat = self._flat_pattern(n, (0, 7, 14))  # 3 of every 20 frames not flat
        self.assertAlmostEqual(sum(flat[:n - n % 20]) / (n - n % 20), 0.85)
        xs = stroke_path(0.5, (1.2 * self.A, -1.2 * self.A) * 3, self.fast)
        self.both_ways(frames_from(xs, flat=flat), [])
        # 1 of every 20 frames not flat (0.95) fires
        flat = self._flat_pattern(n, (0,))
        self.assertGreaterEqual(len(run_wave(self.wave(), frames_from(xs, flat=flat))), 1)

    def test_no_flat_frame_at_all(self):
        xs = stroke_path(0.5, (1.2 * self.A, -1.2 * self.A), self.fast)
        self.both_ways(frames_from(xs, flat=[False] * len(xs)), [])

    def test_waving_on_does_not_fire_again_until_release_and_cooldown(self):
        xs = stroke_path(0.5, (1.2 * self.A, -1.2 * self.A) * 10, self.fast)  # 20 strokes, 6 s of flat waving
        frames = frames_from(xs)
        fired = self.both_ways(frames, run_wave(self.wave(), frames))
        self.assertEqual(len(fired), 1)

    def test_rearm_needs_end_of_flat_hand_after_cooldown(self):
        tr = self.wave()
        frames = self.two_strokes(1.2 * self.A)
        fired = run_wave(tr, frames)
        self.assertEqual(len(fired), 1)
        t_emit = frames[fired[0]][0]
        t = frames[-1][0] + DT
        # a non-flat frame INSIDE the cooldown does not release the flat hand
        self.assertLess(t - t_emit, self.cooldown)
        self.assertFalse(tr.update(t, hand(CURLED, 0.5, 0.5), False))
        t0 = t_emit + self.cooldown + DT
        more = frames_from(stroke_path(0.5, (1.2 * self.A, -1.2 * self.A) * 3, self.fast), t0=t0)
        self.assertEqual(run_wave(tr, more), [])
        # a non-flat frame after the cooldown releases it: the next wave fires
        t = more[-1][0] + DT
        self.assertFalse(tr.update(t, hand(CURLED, 0.5, 0.5), False))
        again = frames_from(stroke_path(0.5, (1.2 * self.A, -1.2 * self.A), self.fast), t0=t + DT)
        self.assertEqual(len(run_wave(tr, again)), 1)
        # a frame without hand releases it too
        t = again[-1][0] + DT
        self.assertFalse(tr.update(t, None, False))
        again2 = frames_from(stroke_path(0.5, (1.2 * self.A, -1.2 * self.A), self.fast), t0=t + self.cooldown)
        self.assertEqual(len(run_wave(tr, again2)), 1)
        self.assertEqual(tr.n_emits, 3)

    def test_cooldown_blocks_even_after_the_hand_left(self):
        tr = self.wave()
        frames = self.two_strokes(1.2 * self.A)
        fired = run_wave(tr, frames)
        t_emit = frames[fired[0]][0]
        t = frames[-1][0] + DT
        self.assertFalse(tr.update(t, None, False))  # hand withdrawn at once
        xs = stroke_path(0.5, (1.2 * self.A, -1.2 * self.A) * 6, self.fast, still_before=1)
        quick = frames_from(xs, t0=t + DT)
        fired2 = run_wave(tr, quick)
        self.assertTrue(fired2)
        for i in fired2:
            self.assertGreaterEqual(quick[i][0] - t_emit, self.cooldown)

    def test_losing_the_hand_in_the_middle_counts_again(self):
        up = frames_from(stroke_path(0.5, (1.2 * self.A,), self.fast, still_after=0))
        x_top = 0.5 + 1.2 * self.A
        t = up[-1][0] + DT
        down = frames_from(stroke_path(x_top, (-1.2 * self.A,), self.fast, still_before=1), t0=t + DT)
        frames = up + [(t, None, False)] + down
        self.both_ways(frames, [])
        # without the lost frame the same strokes fire
        self.assertEqual(len(run_wave(self.wave(), up + down)), 1)

    def test_strokes_property_for_the_hud(self):
        tr = self.wave()
        frames = self.two_strokes(1.2 * self.A)
        seen = []
        for ts, p, f in frames:
            fired = tr.update(ts, p, f)
            seen.append(tr.strokes)
            if fired:
                break
        self.assertEqual(seen[0], 0)
        self.assertIn(1, seen)
        self.assertEqual(tr.strokes, 0)  # buffer cleared after the backspace

    def test_bad_timestamp_and_bad_parameters(self):
        with self.assertRaises(ValueError):
            self.wave().update(float("inf"), hand(FLAT, 0.5, 0.5), True)
        good = dict(window_ms=1500, min_amplitude=0.6, min_strokes=2, max_vertical_ratio=0.5,
                    min_flat_fraction=0.9, cooldown_ms=1000)
        WaveBackspaceGesture(**good)
        for key, bad in (("window_ms", 0), ("min_amplitude", -1), ("min_strokes", 0), ("min_strokes", 1.5),
                         ("max_vertical_ratio", 1.5), ("min_flat_fraction", 0), ("cooldown_ms", float("nan"))):
            with self.assertRaises(ValueError):
                WaveBackspaceGesture(**dict(good, **{key: bad}))


# ================================================================================================ engine
class TestGestureEngine(unittest.TestCase):
    W, H = 640, 480

    def setUp(self):
        self.v = load_values()

    def raw(self, template, cx, cy):
        return to_mediapipe(hand(template, cx, cy), self.W, self.H)

    def test_keys_and_no_hand(self):
        eng = GestureEngine(self.v)
        out = eng.step(0.0, None, self.W, self.H, True)
        self.assertEqual(out, {"space": False, "backspace": False, "is_palm": False, "is_flat": False})

    def test_open_palm_still_gives_one_space(self):
        eng = GestureEngine(self.v)
        outs = [eng.step(i * DT, self.raw(OPEN_PALM, 0.6, 0.5), self.W, self.H, True) for i in range(80)]
        self.assertTrue(all(o["is_palm"] and not o["is_flat"] for o in outs))
        self.assertEqual(sum(o["space"] for o in outs), 1)
        self.assertEqual([i for i, o in enumerate(outs) if o["space"]], [int(math.ceil(self.v["space_hold_ms"] / DT))])
        self.assertFalse(any(o["backspace"] for o in outs))

    def test_open_palm_moving_gives_nothing(self):
        eng = GestureEngine(self.v)
        outs = [eng.step(i * DT, self.raw(OPEN_PALM, 0.6, 0.5), self.W, self.H, False) for i in range(80)]
        self.assertFalse(any(o["space"] for o in outs))

    def test_flat_wave_gives_one_backspace(self):
        eng = GestureEngine(self.v)
        a = self.v["wave_min_amplitude"] * PALM
        xs = stroke_path(0.6, (1.2 * a, -1.2 * a) * 4, 12)
        outs = [eng.step(i * DT, self.raw(FLAT, x, 0.5), self.W, self.H, False) for i, x in enumerate(xs)]
        self.assertTrue(all(o["is_flat"] and not o["is_palm"] for o in outs))
        self.assertEqual(sum(o["backspace"] for o in outs), 1)
        self.assertFalse(any(o["space"] for o in outs))
        # the engine's wave is the tracker on aspect-corrected points
        tr = WaveBackspaceGesture.from_values(self.v)
        expected = [i for i, x in enumerate(xs) if tr.update(i * DT, hand(FLAT, x, 0.5), True)]
        self.assertEqual([i for i, o in enumerate(outs) if o["backspace"]], expected)

    def test_flat_thresholds_come_from_the_values(self):
        for key, value in (("flat_thumb_max_spread", 0.9), ("flat_thumb_min_ratio", 1.2)):
            v = dict(self.v, **{key: value})
            out = GestureEngine(v).step(0.0, self.raw(FLAT, 0.6, 0.5), self.W, self.H, True)
            self.assertFalse(out["is_flat"], key)
        self.assertTrue(GestureEngine(self.v).step(0.0, self.raw(FLAT, 0.6, 0.5), self.W, self.H, True)["is_flat"])

    def test_curled_hand_is_neither(self):
        out = GestureEngine(self.v).step(0.0, self.raw(CURLED, 0.6, 0.5), self.W, self.H, True)
        self.assertEqual(out, {"space": False, "backspace": False, "is_palm": False, "is_flat": False})

    def test_reset_and_trackers_exposed(self):
        eng = GestureEngine(self.v)
        for i in range(5):
            eng.step(i * DT, self.raw(OPEN_PALM, 0.6, 0.5), self.W, self.H, True)
        self.assertGreater(eng.space.held_ms, 0)
        eng.reset()
        self.assertEqual(eng.space.held_ms, 0.0)
        self.assertEqual(eng.wave.strokes, 0)

    def test_missing_value_key(self):
        v = dict(self.v)
        del v["wave_window_ms"]
        with self.assertRaises(ValueError):
            GestureEngine(v)


# ================================================================================================ lần sửa 13d, G2a
VARIANTS = ((1.0, False), (0.5, False), (1.0, True), (0.5, True))  # scale, mirror in x (as both_ways)


def first_emission(tracker, frames):
    """Feed the frames until the tracker fires -> index of that frame, or None."""
    for i, (ts, p, f) in enumerate(frames):
        if tracker.update(ts, p, f):
            return i
    return None


class TestWaveSpanAcD1(unittest.TestCase):
    """AC-D1 (TB-1 of the G1 review): the flat fraction and the vertical / horizontal ratio are computed on the frames from
    the start of the first stroke to now. Every sequence is a chuỗi tạo có kiểm soát để kiểm logic."""

    N_PRE = 10  # still frames just before the strokes (AC-D1: at least 10)

    def setUp(self):
        self.v = load_values()
        self.A = self.v["wave_min_amplitude"] * PALM
        self.window = self.v["wave_window_ms"]
        self.fast = 12

    def wave(self):
        return WaveBackspaceGesture.from_values(self.v)

    def _strokes(self, t0, still_before):
        return frames_from(stroke_path(0.5, (1.2 * self.A, -1.2 * self.A), self.fast, still_before=still_before), t0=t0)

    def _buffer_at_emission(self, frames, i):
        """Frames the tracker holds when it fires at frame i (all of them must still be inside the window)."""
        ts_e = frames[i][0]
        buf = [f for f in frames[:i + 1] if f[0] >= ts_e - self.window]
        self.assertEqual(len(buf), i + 1, "all frames inside wave_window_ms")
        return buf

    def test_d1a_non_flat_still_frames_before_the_strokes_do_not_block(self):
        pre = frames_from([0.5] * self.N_PRE, flat=[False] * self.N_PRE, template=CURLED)
        frames = pre + self._strokes(self.N_PRE * DT, still_before=0)
        for scale, flip in VARIANTS:
            fr = transform(frames, scale, flip)
            tr = self.wave()
            i = first_emission(tr, fr)
            self.assertIsNotNone(i, f"scale={scale} flip={flip}")
            buf = self._buffer_at_emission(fr, i)
            # precondition: on the WHOLE buffer the flat fraction is below the threshold
            self.assertLess(sum(f for _, _, f in buf) / len(buf), self.v["wave_min_flat_fraction"])
            self.assertEqual(len(run_wave(self.wave(), fr)), 1, f"scale={scale} flip={flip}")

    def test_d1b_vertically_offset_still_frames_before_the_strokes_do_not_block(self):
        pre = frames_from([0.5] * self.N_PRE, ys=[0.5 + 2 * self.A] * self.N_PRE)
        frames = pre + self._strokes(self.N_PRE * DT, still_before=1)
        for scale, flip in VARIANTS:
            fr = transform(frames, scale, flip)
            tr = self.wave()
            i = first_emission(tr, fr)
            self.assertIsNotNone(i, f"scale={scale} flip={flip}")
            buf = self._buffer_at_emission(fr, i)
            c = np.array([palm_centre(p) for _, p, _ in buf])
            dx = c[:, 0].max() - c[:, 0].min()
            dy = c[:, 1].max() - c[:, 1].min()
            # precondition: on the WHOLE buffer vertical / horizontal is above the threshold
            self.assertGreater(dy, self.v["wave_max_vertical_ratio"] * dx)
            self.assertEqual(len(run_wave(self.wave(), fr)), 1, f"scale={scale} flip={flip}")

    def test_d1c_the_same_non_flat_frames_inside_the_strokes_block(self):
        pre = frames_from([0.5] * self.N_PRE)
        strokes = self._strokes(self.N_PRE * DT, still_before=0)
        inside = set(range(1, 2 * self.N_PRE, 2))  # every other frame of the strokes
        self.assertLess(max(inside), 2 * self.fast)
        strokes = [(ts, p, f and k not in inside) for k, (ts, p, f) in enumerate(strokes)]
        frames = pre + strokes
        self.assertEqual(sum(not f for _, _, f in frames), self.N_PRE)
        for scale, flip in VARIANTS:
            self.assertEqual(run_wave(self.wave(), transform(frames, scale, flip)), [], f"scale={scale} flip={flip}")


class TestSpaceRearmBoundaryAcD2(unittest.TestCase):
    """AC-D2 (THẤP-3): after a space, another pose for exactly space_rearm_ms does not re-arm; for space_rearm_ms + DT it
    does. Timestamps are set exactly (not accumulated)."""

    def setUp(self):
        self.v = load_values()
        self.hold = self.v["space_hold_ms"]
        self.rearm = self.v["space_rearm_ms"]
        self.k_hold = int(math.ceil(self.hold / DT))

    def _run(self, last_other_offset):
        tr = DeliberateSpaceGesture.from_values(self.v)
        fired = [k for k in range(self.k_hold + 1) if tr.update(k * DT, True, True, True)]
        self.assertEqual(fired, [self.k_hold])
        t1 = (self.k_hold + 1) * DT  # first frame of the other pose (other_since)
        other = [t1 + k * DT for k in range(int(math.ceil(self.rearm / DT))) if k * DT < self.rearm]
        other.append(t1 + last_other_offset)
        for ts in other:
            self.assertFalse(tr.update(ts, False, True, True))
        t2 = other[-1] + DT
        second = [k for k in range(self.k_hold * 3) if tr.update(t2 + k * DT, True, True, True)]
        return tr, second

    def test_d2_other_pose_for_exactly_rearm_does_not_rearm(self):
        tr, second = self._run(self.rearm)
        self.assertEqual(second, [])
        self.assertEqual(tr.n_emits, 1)

    def test_d2_other_pose_for_rearm_plus_one_frame_rearms(self):
        tr, second = self._run(self.rearm + DT)
        self.assertEqual(second, [self.k_hold])
        self.assertEqual(tr.n_emits, 2)


class TestParametersAreReadAcD3(unittest.TestCase):
    """AC-D3 (THẤP-4): wave_min_strokes and space_dropout_frames come from the values, not from the code."""

    def setUp(self):
        self.v = load_values()
        self.A = self.v["wave_min_amplitude"] * PALM
        self.k_hold = int(math.ceil(self.v["space_hold_ms"] / DT))

    def _waves(self, n_strokes):
        amps = tuple((1.2 * self.A) * (1 if k % 2 == 0 else -1) for k in range(n_strokes))
        return frames_from(stroke_path(0.5, amps, 12))

    def test_d3_wave_min_strokes_from_values(self):
        n = self.v["wave_min_strokes"] + 1  # = 3 with the design table
        v = dict(self.v, wave_min_strokes=n)
        self.assertEqual(len(run_wave(WaveBackspaceGesture.from_values(self.v), self._waves(n - 1))), 1)
        self.assertEqual(run_wave(WaveBackspaceGesture.from_values(v), self._waves(n - 1)), [])
        self.assertEqual(len(run_wave(WaveBackspaceGesture.from_values(v), self._waves(n))), 1)

    def test_d3_space_dropout_frames_from_values(self):
        d = self.v["space_dropout_frames"] + 1  # = 2 with the design table
        v = dict(self.v, space_dropout_frames=d)
        mid = self.k_hold // 2

        def feed(values, n_bad):
            tr = DeliberateSpaceGesture.from_values(values)
            seq = [True] * mid + [False] * n_bad + [True] * (self.k_hold * 2)
            return [k for k, palm in enumerate(seq) if tr.update(k * DT, palm, True, True)]

        self.assertEqual(feed(v, d), [self.k_hold])               # d bad frames in a row: the hold goes on
        self.assertEqual(feed(v, d + 1), [mid + d + 1 + self.k_hold])  # one more: the hold starts again
        self.assertEqual(feed(self.v, d), [mid + d + self.k_hold])     # with the design value d frames already restart


class TestCooldownNotBufferedAcD4(unittest.TestCase):
    """AC-D4 (P2): hand frames inside the wave cooldown are not buffered (strokes == 0), so two strokes done entirely inside
    the cooldown do not fire when it ends; two strokes started after the cooldown fire once."""

    MARGIN_MS = 300.0  # AC-D4: the flat hand stays still until t_emit + wave_cooldown_ms + 300 ms

    def setUp(self):
        self.v = load_values()
        self.A = self.v["wave_min_amplitude"] * PALM
        self.cooldown = self.v["wave_cooldown_ms"]
        self.fast = 12

    def test_d4_strokes_inside_the_cooldown_never_fire(self):
        two = (1.2 * self.A, -1.2 * self.A)
        for scale, flip in VARIANTS:
            msg = f"scale={scale} flip={flip}"
            tr = WaveBackspaceGesture.from_values(self.v)
            first = transform(frames_from(stroke_path(0.5, two, self.fast)), scale, flip)
            i = first_emission(tr, first)
            self.assertIsNotNone(i, msg)
            t_emit = first[i][0]
            self.assertFalse(tr.update(t_emit + DT, None, False))  # the hand leaves at once (releases the flat hand)
            inside = transform(frames_from(stroke_path(0.5, two, self.fast, still_before=1, still_after=0),
                                           t0=t_emit + 2 * DT), scale, flip)
            self.assertLess(inside[-1][0] - t_emit, self.cooldown, "both strokes entirely inside the cooldown")
            for ts, p, f in inside:
                self.assertFalse(tr.update(ts, p, f), msg)
                self.assertEqual(tr.strokes, 0, msg)
            still_p = inside[-1][1]
            ts = inside[-1][0] + DT
            while ts <= t_emit + self.cooldown + self.MARGIN_MS:
                self.assertFalse(tr.update(ts, still_p, True), msg)
                if ts - t_emit < self.cooldown:
                    self.assertEqual(tr.strokes, 0, msg)
                ts += DT
            self.assertEqual(tr.n_emits, 1, msg)
            # control: two strokes started after the cooldown fire exactly once
            after = transform(frames_from(stroke_path(0.5, two, self.fast), t0=ts), scale, flip)
            self.assertEqual(len(run_wave(tr, after)), 1, msg)
            self.assertEqual(tr.n_emits, 2, msg)


class TestNonFiniteFrameAcD5(unittest.TestCase):
    """AC-D5 (THẤP-2): GestureEngine.step treats a landmark frame with NaN / inf as no hand for both trackers; width and
    height must be finite and > 0; a wrong shape is still a ValueError."""

    W, H = 640, 480

    def setUp(self):
        self.v = load_values()
        self.k_hold = int(math.ceil(self.v["space_hold_ms"] / DT))

    def raw(self, template, cx, cy):
        return to_mediapipe(hand(template, cx, cy), self.W, self.H)

    def bad_frames(self, template, cx, cy):
        out = []
        for idx, col, val in ((8, 0, float("nan")), (0, 1, float("inf")), (12, 2, float("nan")), (4, 2, -float("inf"))):
            r = self.raw(template, cx, cy)
            r[idx, col] = val
            out.append(r)
        return out

    def test_d5_non_finite_frame_is_neither_pose(self):
        for template in (OPEN_PALM, FLAT):
            for r in self.bad_frames(template, 0.6, 0.5):
                out = GestureEngine(self.v).step(0.0, r, self.W, self.H, True)
                self.assertEqual(out, {"space": False, "backspace": False, "is_palm": False, "is_flat": False})

    def _space_run(self, mid_frame):
        eng = GestureEngine(self.v)
        seq = [self.raw(OPEN_PALM, 0.6, 0.5)] * (self.k_hold * 3)
        seq = seq[:self.k_hold // 2] + [mid_frame] + seq[self.k_hold // 2 + 1:]
        return [k for k, r in enumerate(seq) if eng.step(k * DT, r, self.W, self.H, True)["space"]]

    def test_d5_non_finite_frame_while_holding_the_open_palm_is_a_lost_hand(self):
        lost = self._space_run(None)
        # sanity: a lost hand and a bad frame with the hand give different emissions, so equality below means something
        self.assertNotEqual(lost, self._space_run(self.raw(CURLED, 0.6, 0.5)))
        for r in self.bad_frames(OPEN_PALM, 0.6, 0.5):
            self.assertEqual(self._space_run(r), lost)

    def test_d5_non_finite_frame_during_a_wave_clears_the_strokes(self):
        a = self.v["wave_min_amplitude"] * PALM
        xs = stroke_path(0.6, (1.2 * a, -1.2 * a), 12)
        k_mid = 4 + 12 + 6  # in the middle of the second stroke
        for bad in self.bad_frames(FLAT, xs[k_mid], 0.5):
            eng = GestureEngine(self.v)
            for k in range(k_mid):
                self.assertFalse(eng.step(k * DT, self.raw(FLAT, xs[k], 0.5), self.W, self.H, False)["backspace"])
            self.assertGreaterEqual(eng.wave.strokes, 1)
            out = eng.step(k_mid * DT, bad, self.W, self.H, False)
            self.assertFalse(out["backspace"])
            self.assertEqual(eng.wave.strokes, 0)

    def test_d5_width_and_height_must_be_finite_and_positive(self):
        r = self.raw(OPEN_PALM, 0.6, 0.5)
        for bad in (0, -1, float("nan"), float("inf")):
            for frame in (r, None):
                with self.assertRaises(ValueError):
                    GestureEngine(self.v).step(0.0, frame, bad, self.H, True)
                with self.assertRaises(ValueError):
                    GestureEngine(self.v).step(0.0, frame, self.W, bad, True)

    def test_d5_wrong_shape_is_still_a_value_error(self):
        r = self.raw(OPEN_PALM, 0.6, 0.5)
        nan_r = r.copy()
        nan_r[0, 0] = float("nan")
        for bad in (r[:, :2], r[:20], nan_r[:, :2], r.reshape(-1)):
            with self.assertRaises(ValueError):
                GestureEngine(self.v).step(0.0, bad, self.W, self.H, True)


if __name__ == "__main__":
    unittest.main()
