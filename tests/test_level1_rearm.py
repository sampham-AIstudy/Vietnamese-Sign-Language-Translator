"""
Plan 15 lần sửa 3 §3.2 / §5 (R1): pose re-arm rules of Level1SignSegmenter — AC-RA1 … AC-RA11.

The landmark sequences below are controlled landmark sequences built in this test to check the segmenter's logic;
they are not real data (chuỗi landmark tạo có kiểm soát để kiểm logic, không phải dữ liệu thật). The parameters are a
test-only set (PARAMS_RA), not configs/level1_realtime.json.

Hand model: the wrist (point 0) and the middle MCP (point 9) of every shape sit at the same place, so the palm length
is constant and the normalised shape N is linear in the raw landmarks. A shape at pose distance d from A along a
direction is A + d * DIR / D_DIR, hence pose_distance(N(A), N(shape)) = |d| and, along a linear transition A -> B, the
distance from A grows linearly in time. Every pose distance used by an assert is computed with the independent formula
of this file (pose_distance_by_hand), not with the function under test.
"""
import os
import subprocess
import sys
import types
import unittest
from unittest import mock

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import src.inference.level1_segmenter as seg_mod  # noqa: E402
from src.inference.level1_core import validate_level1_config  # noqa: E402
from src.inference.level1_segmenter import Level1SignSegmenter, SignSegment, WordGap  # noqa: E402

W, H = 640, 480
DT = 40.0
PALM = 0.15
WRIST = np.array([0.5, 0.5, 0.0])
MIN_DETECTED = 3
THR = 0.15  # rearm_pose_dist of PARAMS_RA, in hand lengths
# test-only parameters: motion window of 3 frame intervals (median of 3 m values), so a single deviating frame does
# not change M_t; the anchor window [t_emit - 120 ms, t_emit] holds 4 frames
PARAMS_RA = {"motion_window_ms": 120, "still_speed": 1.0, "move_speed": 2.0, "hold_ms": 400, "rearm_move_ms": 120,
             "hand_lost_ms": 200, "word_gap_ms": 600, "max_segment_ms": 3000, "min_sign_frames": 4,
             "tail_still_keep_ms": 400, "pose_change_rules": True, "rearm_pose_dist": THR,
             "pose_over_jitter_ratio": 2.0}
A2A_COMMIT = "b545ce7"  # `15: A2a` — the segmenter the rules-off path must reproduce (lần sửa 3 §3.2)


def _offsets_a():
    """Shape A: offsets from the wrist; point 9 (middle MCP) at distance PALM straight up."""
    offs = np.zeros((21, 3), dtype=np.float64)
    for i in range(1, 21):
        ang = -np.pi / 2 + (i - 10) * 0.08
        r = PALM * (0.6 + 0.05 * (i % 5))
        offs[i] = [r * np.cos(ang), r * np.sin(ang), -0.01 * (i % 4)]
    offs[9] = [0.0, -PALM, 0.0]
    return offs


def _direction():
    """A shape change that keeps the wrist (0) and the middle MCP (9) in place."""
    d = np.zeros((21, 3), dtype=np.float64)
    for i in range(1, 21):
        if i != 9:
            d[i] = [0.3 * PALM * np.sin(1.3 * i), 0.4 * PALM * np.cos(1.7 * i), 0.2 * PALM * np.sin(0.5 * i)]
    return d


OFFS_A = _offsets_a()
DIR = _direction()


def normalized_by_hand(raw):
    """Aspect correction (x, z * W/H) then wrist-centred, divided by |P9 - P0| (3D) — written out in this test."""
    p = np.asarray(raw, dtype=np.float64).copy()
    p[:, 0] *= W / H
    p[:, 2] *= W / H
    c = p - p[0]
    return c / np.linalg.norm(c[9])


def pose_distance_by_hand(raw_a, raw_b):
    return float(np.mean(np.linalg.norm(normalized_by_hand(raw_a) - normalized_by_hand(raw_b), axis=-1)))


def _raw(offs, wrist_y=0.0):
    lm = offs + WRIST
    lm = lm.copy()
    lm[:, 1] += wrist_y
    return lm


D_DIR = pose_distance_by_hand(_raw(OFFS_A), _raw(OFFS_A + DIR))


def shape(dist, wrist_y=0.0, direction=None):
    """Raw landmarks [21, 3] float32 of the shape at pose distance |dist| from A along `direction` (default DIR)."""
    d = DIR if direction is None else direction
    d_unit = pose_distance_by_hand(_raw(OFFS_A), _raw(OFFS_A + d))
    return _raw(OFFS_A + d * (dist / d_unit), wrist_y).astype(np.float32)


A = shape(0.0)


def frames_from(raws, start_index=0):
    return [((start_index + k) * DT, lm, "Left" if lm is not None else "") for k, lm in enumerate(raws)]


def run(seg, frames, after=None):
    """frames: [(ts, landmarks | None, handedness)] -> [(frame_index, event)]; `after(i, seg)` is called after each
    push."""
    out = []
    for i, (ts, lm, hd) in enumerate(frames):
        for ev in seg.push(ts, lm, hd, W, H):
            out.append((i, ev))
        if after is not None:
            after(i, seg)
    return out


def segments(events):
    return [e for _, e in events if isinstance(e, SignSegment)]


def gaps(events):
    return [e for _, e in events if isinstance(e, WordGap)]


def new_seg(**over):
    return Level1SignSegmenter({**PARAMS_RA, **over}, MIN_DETECTED)


# ------------------------------------------------------------------ streams (frame interval DT = 40 ms)
D_RA1 = 0.3  # B of AC-RA1: 5-frame transition -> shape speed 0.3 / 0.2 s = 1.5 (between still 1.0 and move 2.0)
D_RA4 = 1.0  # B of AC-RA4: 50-frame (2 s) transition -> shape speed 0.5 <= still 1.0; THR reached after 0.3 s


def stream_ra1():
    """A held 1 s (frames 0..24) -> A to B in 200 ms (frames 25..29, wrist still) -> B held 1 s (frames 30..54)."""
    raws = [A] * 25 + [shape(D_RA1 * (k - 24) / 5.0) for k in range(25, 30)] + [shape(D_RA1)] * 25
    return frames_from(raws)


def stream_ra2():
    """A held 5 s."""
    return frames_from([A] * 126)


def stream_ra3():
    """A with shape noise (pose distance from A < THR / 2 on every frame) for 5 s, one single frame at 2 * THR."""
    rng = np.random.default_rng(0)
    raws = []
    for k in range(126):
        noise = rng.normal(size=(21, 3))
        noise[0] = 0.0
        noise[9] = 0.0
        raws.append(shape(0.012, direction=noise))
    raws[63] = shape(2.0 * THR)
    return frames_from(raws)


def stream_ra4():
    """A held 1 s (0..24) -> A to B slowly in 2 s (25..74) -> B held 1 s (75..99)."""
    raws = [A] * 25 + [shape(D_RA4 * (k - 24) / 50.0) for k in range(25, 75)] + [shape(D_RA4)] * 25
    return frames_from(raws)


BOUNCE_SPEED = 0.6  # image units / s -> wrist speed 4 hand lengths / s >= move 2.0


def stream_ra5():
    """A held 1 s -> wrist bounce (shape A, 8 frames = 320 ms of motion) -> A held 1 s at the new place."""
    raws = [A] * 25
    for k in range(1, 9):
        raws.append(shape(0.0, wrist_y=BOUNCE_SPEED * k * DT / 1000.0))
    raws += [shape(0.0, wrist_y=BOUNCE_SPEED * 8 * DT / 1000.0)] * 25
    return frames_from(raws)


def stream_ra7():
    """A held (0..25, 1000 ms) -> no hand 1040..1320 (>= hand_lost 200, < word_gap 600) -> A held 1 s again."""
    return frames_from([A] * 26 + [None] * 8 + [A] * 26)


def emit_index_of_plain_hold():
    """Index of the frame that emits the first 'hold' of stream_ra2 (computed by the segmenter, rules on)."""
    ev = run(new_seg(), stream_ra2())
    return [i for i, e in ev if isinstance(e, SignSegment)][0]


def stream_ra8():
    """A held; the emitting frame itself deviates by 0.9 * THR (one frame); afterwards the hand settles at 0.3 * THR on
    the other side of A for 3 s. One frame anchor -> distance 1.2 * THR >= THR (would re-arm); window-mean anchor ->
    0.525 * THR (does not)."""
    k_emit = emit_index_of_plain_hold()
    raws = [A] * k_emit + [shape(0.9 * THR)] + [shape(-0.3 * THR)] * 75
    return frames_from(raws), k_emit


def _git_show(spec):
    r = subprocess.run(["git", "show", spec], cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError(f"git show {spec} failed (missing commit / shallow clone?): {r.stderr.strip()}")
    return r.stdout


_A2A_MODULE = None


def a2a_segmenter_module():
    """The segmenter of commit A2A_COMMIT loaded from `git show` into a temporary in-memory module (nothing written
    to the repo). A missing commit fails the test; it is never skipped."""
    global _A2A_MODULE
    if _A2A_MODULE is None:
        src = _git_show(f"{A2A_COMMIT}:src/inference/level1_segmenter.py")
        name = f"_level1_segmenter_ref_{A2A_COMMIT}"
        mod = types.ModuleType(name)
        mod.__file__ = f"<git show {A2A_COMMIT}:src/inference/level1_segmenter.py>"
        sys.modules[name] = mod
        try:
            exec(compile(src, mod.__file__, "exec"), mod.__dict__)
        finally:
            sys.modules.pop(name, None)
        _A2A_MODULE = mod
    return _A2A_MODULE


def assert_events_identical(tc, got, ref, where):
    tc.assertEqual(len(got), len(ref), f"{where}: number of events")
    for k, ((ia, a), (ib, b)) in enumerate(zip(got, ref)):
        tc.assertEqual(ia, ib, f"{where}: event {k} frame index")
        tc.assertEqual(type(a).__name__, type(b).__name__, f"{where}: event {k} type")
        if type(a).__name__ == "WordGap":
            tc.assertEqual((a.seq, a.t_ms), (b.seq, b.t_ms), f"{where}: event {k}")
            continue
        for field in ("raw_landmarks", "detected", "handedness", "timestamps_ms"):
            tc.assertTrue(np.array_equal(getattr(a, field), getattr(b, field)), f"{where}: event {k} {field}")
            tc.assertEqual(getattr(a, field).dtype, getattr(b, field).dtype, f"{where}: event {k} {field} dtype")
        tc.assertEqual((a.seq, a.close_reason, a.t_start_ms, a.t_end_ms, a.t_emit_ms, a.frame_width, a.frame_height),
                       (b.seq, b.close_reason, b.t_start_ms, b.t_end_ms, b.t_emit_ms, b.frame_width, b.frame_height),
                       f"{where}: event {k} fields")


class TestStreamsAreWhatTheyClaim(unittest.TestCase):
    """The controlled sequences have the properties the AC-RA cases rely on (checked with the by-hand formula)."""

    def test_shape_helper_is_linear(self):
        for d in (0.0, 0.06, THR, 0.3, 1.0):
            self.assertAlmostEqual(pose_distance_by_hand(A, shape(d)), d, places=6)
        self.assertAlmostEqual(pose_distance_by_hand(shape(0.9 * THR), shape(-0.3 * THR)), 1.2 * THR, places=6)


class TestPoseDistanceRA9(unittest.TestCase):
    """AC-RA9: pose_distance = mean over the 21 points of the 3D distance; the segmenter calls the module function."""

    def test_ra9_formula_on_random_arrays(self):
        rng = np.random.default_rng(12345)
        for _ in range(20):
            a, b = rng.normal(size=(21, 3)), rng.normal(size=(21, 3))
            expected = float(np.mean(np.sqrt(np.sum((a - b) ** 2, axis=-1))))
            self.assertAlmostEqual(seg_mod.pose_distance(a, b), expected, places=12)
            self.assertEqual(seg_mod.pose_distance(a, a), 0.0)
            self.assertAlmostEqual(seg_mod.pose_distance(a, b), seg_mod.pose_distance(b, a), places=12)

    def test_ra9_segmenter_uses_module_function_only_when_on(self):
        real = seg_mod.pose_distance
        frames = stream_ra1()
        ref_on = run(new_seg(), frames)
        with mock.patch.object(seg_mod, "pose_distance", side_effect=real) as spy:
            got_on = run(new_seg(), frames)
        self.assertGreater(spy.call_count, 0)
        assert_events_identical(self, got_on, ref_on, "on, spied")
        with mock.patch.object(seg_mod, "pose_distance", side_effect=real) as spy:
            run(new_seg(pose_change_rules=False), frames)
        self.assertEqual(spy.call_count, 0, "rules off: pose_distance is never called")


class TestPoseRearm(unittest.TestCase):
    def test_ra1_shape_change_without_motion_rearms(self):
        """AC-RA1: A -> B in 200 ms, wrist still, shape speed below move_speed, no hand loss: 2 'hold' segments,
        segment 2 starts at the first frame with d >= rearm_pose_dist; with the rules off: 1 segment (U1b)."""
        frames = stream_ra1()
        # the transition is NOT a motion re-arm: per-frame shape speed and M_t stay below move_speed
        speeds = [pose_distance_by_hand(frames[k - 1][1], frames[k][1]) / (DT / 1000.0) for k in range(25, 31)]
        self.assertLess(max(speeds), PARAMS_RA["move_speed"])
        self.assertGreater(max(speeds), 0.0)
        motions = []
        ev = run(new_seg(), frames, after=lambda i, s: motions.append(s.motion))
        self.assertLess(max(m for m in motions if m is not None), PARAMS_RA["move_speed"])
        segs = segments(ev)
        self.assertEqual([s.close_reason for s in segs], ["hold", "hold"])
        self.assertEqual(gaps(ev), [])
        first_far = next(ts for ts, lm, _ in frames if pose_distance_by_hand(lm, A) >= THR)
        self.assertEqual(segs[1].t_start_ms, first_far)
        self.assertLess(pose_distance_by_hand(segs[1].raw_landmarks[-1], shape(D_RA1)), THR)
        self.assertEqual(len(segments(run(new_seg(pose_change_rules=False), frames))), 1)

    def test_ra2_long_hold_no_repeat(self):
        """AC-RA2: A held 5 s -> 1 segment (rules on and off)."""
        for on in (True, False):
            with self.subTest(pose_change_rules=on):
                self.assertEqual(len(segments(run(new_seg(pose_change_rules=on), stream_ra2()))), 1)

    def test_ra3_noise_and_single_outlier(self):
        """AC-RA3: shape noise d < THR / 2 for 5 s plus one frame at >= THR -> 1 segment."""
        frames = stream_ra3()
        d = [pose_distance_by_hand(lm, A) for _, lm, _ in frames]
        self.assertGreaterEqual(d[63], THR)
        self.assertLess(max(d[:63] + d[64:]), THR / 2.0)
        self.assertEqual(len(segments(run(new_seg(), frames))), 1)

    def test_ra4_slow_transition_no_halfway_segment(self):
        """AC-RA4: A -> B in 2 s with shape speed <= still_speed and THR crossed in less than hold_ms: rules on -> 2
        segments, the last frame of segment 2 within THR of B; rules off -> 1 segment."""
        frames = stream_ra4()
        speeds = [pose_distance_by_hand(frames[k - 1][1], frames[k][1]) / (DT / 1000.0) for k in range(25, 76)]
        self.assertLessEqual(max(speeds), PARAMS_RA["still_speed"])
        t0 = frames[24][0]  # last frame of A
        t_thr = next(ts for ts, lm, _ in frames if pose_distance_by_hand(lm, A) >= THR)
        self.assertLess(t_thr - t0, PARAMS_RA["hold_ms"])
        motions = []
        ev = run(new_seg(), frames, after=lambda i, s: motions.append(s.motion))
        self.assertLessEqual(max(m for m in motions[25:76] if m is not None), PARAMS_RA["still_speed"])
        segs = segments(ev)
        self.assertEqual([s.close_reason for s in segs], ["hold", "hold"])
        self.assertLess(pose_distance_by_hand(segs[1].raw_landmarks[-1], shape(D_RA4)), THR)
        self.assertEqual(len(segments(run(new_seg(pose_change_rules=False), frames))), 1)

    def test_ra5_bounce_rearm_kept(self):
        """AC-RA5: hold A, wrist bounce (same shape, M >= move_speed for >= rearm_move_ms), hold A: 2 segments with
        the rules on and off."""
        frames = stream_ra5()
        for on in (True, False):
            with self.subTest(pose_change_rules=on):
                segs = segments(run(new_seg(pose_change_rules=on), frames))
                self.assertEqual([s.close_reason for s in segs], ["hold", "hold"])

    def test_ra7_hand_lost_rearms_and_clears_anchor(self):
        """AC-RA7: hand lost >= hand_lost_ms then the same A again -> A emitted again; the anchor is cleared."""
        frames = stream_ra7()
        for on in (True, False):
            with self.subTest(pose_change_rules=on):
                anchors = {}
                ev = run(new_seg(pose_change_rules=on), frames,
                         after=lambda i, s: anchors.__setitem__(i, s._anchor))
                self.assertEqual([s.close_reason for s in segments(ev)], ["hold", "hold"])
                self.assertEqual(gaps(ev), [])
                if on:
                    self.assertIsNotNone(anchors[25])       # after the first emission, before the loss
                self.assertIsNone(anchors[26 + 4])           # loss at 1200 ms (frame 30): anchor cleared

    def test_ra7_reset_clears_anchor_and_pose_since(self):
        """AC-RA7: reset() clears the anchor and _pose_since."""
        seg = new_seg()
        frames = stream_ra1()
        state = {}

        def after(i, s):
            if i == 27:  # 1080 ms: first frame at d >= THR, before the re-arm (1200 ms)
                state["anchor"], state["pose_since"] = s._anchor, s._pose_since
        run(seg, frames[:28], after=after)
        self.assertIsNotNone(state["anchor"])
        self.assertEqual(state["pose_since"], frames[27][0])
        seg.reset()
        self.assertIsNone(seg._anchor)
        self.assertIsNone(seg._pose_since)

    def test_ra8_anchor_is_window_mean(self):
        """AC-RA8: anchor = mean N of [t_emit - motion_window_ms, t_emit]: one deviating frame at t_emit does not
        re-arm."""
        frames, k_emit = stream_ra8()
        ev = run(new_seg(), frames)
        segs = segments(ev)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].t_emit_ms, frames[k_emit][0])
        settle = frames[k_emit + 1][1]
        # the controlled sequence discriminates: a one-frame anchor would be >= THR away, the window mean is not
        self.assertGreaterEqual(pose_distance_by_hand(settle, frames[k_emit][1]), THR)
        window = [lm for ts, lm, _ in frames[:k_emit + 1] if ts >= frames[k_emit][0] - PARAMS_RA["motion_window_ms"]]
        self.assertEqual(len(window), 4)
        mean_n = np.mean([normalized_by_hand(lm) for lm in window], axis=0)
        self.assertLess(float(np.mean(np.linalg.norm(normalized_by_hand(settle) - mean_n, axis=-1))), THR)


class TestRulesOffRA6(unittest.TestCase):
    """AC-RA6: rules off -> events identical (every field) for two values of rearm_pose_dist, and identical to the
    segmenter of the A2a commit, on every stream of AC-RA1..RA5/RA7/RA8 and AC-S16/S17."""

    def _streams(self):
        from tests import test_level1_segmenter as s16
        out = {"ra1": (stream_ra1(), {}), "ra2": (stream_ra2(), {}), "ra3": (stream_ra3(), {}),
               "ra4": (stream_ra4(), {}), "ra5": (stream_ra5(), {}), "ra7": (stream_ra7(), {}),
               "ra8": (stream_ra8()[0], {})}
        for name, grid in (("dt_33_47", s16.irregular_grid_33_47(s16.T_MAX)), ("fps_23.584", s16.fps_grid(s16.T_MAX))):
            frames = [(t, lm, hd) for t, lm, hd in s16.phase_frames(grid)]
            for tail in (s16.HOLD_S16, s16.HOLD_S16 / 2.0):
                out[f"s16_s17_{name}_tail{tail}"] = (frames, {"hold_ms": s16.HOLD_S16, "tail_still_keep_ms": tail})
        return out

    def test_ra6_off_identical_for_two_rearm_pose_dist_and_to_a2a(self):
        ref_mod = a2a_segmenter_module()
        for name, (frames, over) in self._streams().items():
            with self.subTest(stream=name):
                p = {**PARAMS_RA, **over, "pose_change_rules": False}
                got_a = run(Level1SignSegmenter({**p, "rearm_pose_dist": THR}, MIN_DETECTED), frames)
                got_b = run(Level1SignSegmenter({**p, "rearm_pose_dist": 7.5}, MIN_DETECTED), frames)
                ref = run(ref_mod.Level1SignSegmenter(p, MIN_DETECTED), frames)
                self.assertGreater(len(got_a), 0)
                assert_events_identical(self, got_a, got_b, f"{name}: two rearm_pose_dist")
                assert_events_identical(self, got_a, ref, f"{name}: vs {A2A_COMMIT}")


class TestConfigRA10(unittest.TestCase):
    """AC-RA10: missing new key -> ValueError; pose_change_rules not a real bool (0 / 1 too) -> ValueError;
    rearm_pose_dist <= 0 -> ValueError (config loader and segmenter)."""

    NEW_KEYS = ("pose_change_rules", "rearm_pose_dist", "pose_over_jitter_ratio")

    def _raw(self):
        import json
        with open(os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_ra10_config_missing_keys(self):
        for key in self.NEW_KEYS:
            raw = self._raw()
            self.assertIn(key, raw)
            del raw[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_level1_config(raw)

    def test_ra10_config_types_and_ranges(self):
        for bad in (0, 1, 1.0, "true", None):
            raw = self._raw()
            raw["pose_change_rules"]["value"] = bad
            with self.subTest(pose_change_rules=bad), self.assertRaises(ValueError):
                validate_level1_config(raw)
        for good in (True, False):
            raw = self._raw()
            raw["pose_change_rules"]["value"] = good
            self.assertIs(validate_level1_config(raw)["pose_change_rules"], good)
        for bad in (0, 0.0, -0.1, True, "0.2"):
            raw = self._raw()
            raw["rearm_pose_dist"]["value"] = bad
            with self.subTest(rearm_pose_dist=bad), self.assertRaises(ValueError):
                validate_level1_config(raw)
        for bad in (1.0, 0.5):
            raw = self._raw()
            raw["pose_over_jitter_ratio"]["value"] = bad
            with self.subTest(pose_over_jitter_ratio=bad), self.assertRaises(ValueError):
                validate_level1_config(raw)

    def test_ra10_segmenter_parameters(self):
        for key in ("pose_change_rules", "rearm_pose_dist"):
            with self.subTest(missing=key), self.assertRaises(ValueError):
                Level1SignSegmenter({k: v for k, v in PARAMS_RA.items() if k != key}, MIN_DETECTED)
        for bad in (0, 1, "true", None):
            with self.subTest(pose_change_rules=bad), self.assertRaises(ValueError):
                new_seg(pose_change_rules=bad)
        for bad in (0, -0.5, float("nan"), float("inf"), True):
            with self.subTest(rearm_pose_dist=bad), self.assertRaises(ValueError):
                new_seg(rearm_pose_dist=bad)


class TestStatusRA11(unittest.TestCase):
    """AC-RA11: status() keeps its 4 keys with the same meaning; with the rules off it equals the A2a segmenter's."""

    def test_ra11_status_keys_and_meaning(self):
        ref_mod = a2a_segmenter_module()
        frames = stream_ra1()
        for on in (True, False):
            seg = new_seg(pose_change_rules=on)
            ref = ref_mod.Level1SignSegmenter({**PARAMS_RA, "pose_change_rules": on}, MIN_DETECTED)
            for ts, lm, hd in frames:
                seg.push(ts, lm, hd, W, H)
                ref.push(ts, lm, hd, W, H)
                st = seg.status()
                self.assertEqual(set(st), {"state", "hold_progress", "armed", "motion"})
                self.assertEqual((st["state"], st["hold_progress"], st["armed"], st["motion"]),
                                 (seg.state, seg.hold_progress, seg.armed, seg.motion))
                self.assertIn(st["state"], seg_mod.STATES)
                if not on:
                    self.assertEqual(st, ref.status(), f"t={ts}")


if __name__ == "__main__":
    unittest.main()
