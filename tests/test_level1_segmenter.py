"""
Plan 15 AC-S: Level1SignSegmenter (src/inference/level1_segmenter.py).

The landmark sequences below are a controlled landmark sequence built in this test to check the segmenter's logic;
they are not real data (chuỗi landmark tạo có kiểm soát để kiểm logic, không phải dữ liệu thật). The parameters
are a test-only parameter set (PARAMS), not configs/level1_realtime.json.

Hand model of the sequences: a fixed 21-point shape whose wrist moves along y. Along y the aspect correction does not
change distances, the palm length is PALM, so a wrist speed of V (image units / s) gives m = V / PALM hand-lengths / s.
"""
import os
import sys
import unittest

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.level1_segmenter import Level1SignSegmenter, SignSegment, WordGap  # noqa: E402

W, H = 640, 480
PALM = 0.15
# test-only parameters (motion window shorter than one frame interval: M_t = m_t, so expected times are exact)
PARAMS = {"motion_window_ms": 30, "still_speed": 1.0, "move_speed": 2.0, "hold_ms": 400, "rearm_move_ms": 120,
          "hand_lost_ms": 200, "word_gap_ms": 600, "max_segment_ms": 3000, "min_sign_frames": 4,
          "tail_still_keep_ms": 400, "pose_change_rules": False, "rearm_pose_dist": 0.2, "pose_over_jitter_ratio": 2.0}
MIN_DETECTED = 3
SPEED = 0.6  # image units / s along y -> m = SPEED / PALM = 4 hand-lengths / s (moving)


def _template():
    """Fixed hand shape: offsets from the wrist; point 9 (middle MCP) at distance PALM straight up."""
    offs = np.zeros((21, 3), dtype=np.float64)
    for i in range(1, 21):
        ang = -np.pi / 2 + (i - 10) * 0.08
        r = PALM * (0.6 + 0.05 * (i % 5))
        offs[i] = [r * np.cos(ang), r * np.sin(ang), -0.01 * (i % 4)]
    offs[9] = [0.0, -PALM, 0.0]
    return offs


TEMPLATE = _template()


def hand_at(y, x=0.5, jitter=0.0):
    lm = TEMPLATE.copy()
    lm[:, 0] += x
    lm[:, 1] += y + jitter
    return lm.astype(np.float32)


def run(seg, frames):
    """frames: list of (ts, landmarks | None, handedness). Returns [(frame_index, event)]."""
    out = []
    for i, (ts, lm, hd) in enumerate(frames):
        for ev in seg.push(ts, lm, hd if lm is not None else "", W, H):
            out.append((i, ev))
    return out


def move_then_still(n_move, n_still, dt=40.0, y0=0.3, start_ts=0.0, start_index=0):
    """n_move frames moving down at SPEED (frame k at y0 + SPEED * k * dt), then n_still frames at the last position."""
    frames = []
    y = y0
    for k in range(n_move):
        y = y0 + SPEED * k * dt / 1000.0
        frames.append((start_ts + (start_index + k) * dt, hand_at(y), "Left"))
    for k in range(n_still):
        frames.append((start_ts + (start_index + n_move + k) * dt, hand_at(y), "Left"))
    return frames, y


def segments(events):
    return [e for _, e in events if isinstance(e, SignSegment)]


def gaps(events):
    return [e for _, e in events if isinstance(e, WordGap)]


def new_seg(**over):
    return Level1SignSegmenter({**PARAMS, **over}, MIN_DETECTED)


class TestSegmenter(unittest.TestCase):
    def test_s1_move_then_hold_one_segment(self):
        frames, _ = move_then_still(10, 20)
        ev = run(new_seg(), frames)
        segs = segments(ev)
        self.assertEqual(len(segs), 1)
        s = segs[0]
        self.assertEqual(s.close_reason, "hold")
        self.assertEqual(s.t_start_ms, 0.0)  # first frame with a hand
        # first still pair = frame 10 (same position as frame 9) -> still since 400 ms; first frame with
        # held >= hold_ms = 400 + 400 = 800 ms = frame 20
        self.assertEqual(s.t_emit_ms, 800.0)
        self.assertEqual(ev[0][0], 20)
        self.assertEqual(s.t_end_ms, 800.0)
        self.assertEqual(s.n_frames, 21)

    def test_s2_long_hold_still_one(self):
        frames, _ = move_then_still(10, 100)
        self.assertEqual(len(segments(run(new_seg(), frames))), 1)

    def test_s3_hold_move_hold_two_segments(self):
        f1, y = move_then_still(10, 20)                                  # frames 0..29, emit at frame 20
        f2, _ = move_then_still(10, 30, y0=y + SPEED * 0.04, start_index=30)  # frames 30..39 move, 40..69 still
        ev = run(new_seg(), f1 + f2)
        segs = segments(ev)
        self.assertEqual([s.close_reason for s in segs], ["hold", "hold"])
        # second segment: re-armed by the motion, buffer cut back to the start of that motion (frame 30 = 1200 ms)
        self.assertEqual(segs[1].t_start_ms, 1200.0)
        self.assertEqual(segs[1].t_emit_ms, 2000.0)  # still since frame 40 (1600 ms) + 400 ms

    def test_s4_short_move_does_not_rearm(self):
        f1, y = move_then_still(10, 20)
        # 2 moving frames (pairs 30 and 31 move: 40 ms of motion < rearm 120 ms), then still
        f2, _ = move_then_still(2, 38, y0=y + SPEED * 0.04, start_index=30)
        segs = segments(run(new_seg(), f1 + f2))
        self.assertEqual(len(segs), 1)

    def test_s5_motion_then_hand_lost(self):
        frames, _ = move_then_still(15, 0)  # frames 0..14 moving, never still
        frames += [((15 + k) * 40.0, None, "") for k in range(10)]
        ev = run(new_seg(), frames)
        segs = segments(ev)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].close_reason, "hand_lost")
        self.assertEqual(segs[0].t_end_ms, 14 * 40.0)  # tail cut at the last hand frame
        self.assertEqual(segs[0].n_frames, 15)
        self.assertTrue(segs[0].detected.all())
        self.assertEqual(ev[0][0], 19)  # 760 - 560 >= hand_lost_ms (200) first at frame 19
        self.assertEqual(segs[0].t_emit_ms, 760.0)

    def test_s6_word_gap_once_after_a_sign(self):
        frames, _ = move_then_still(10, 20)  # sign emitted at frame 20; last hand frame 29 (1160 ms)
        frames += [((30 + k) * 40.0, None, "") for k in range(60)]
        ev = run(new_seg(), frames)
        self.assertEqual(len(segments(ev)), 1)
        g = gaps(ev)
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0].t_ms, 1760.0)  # first no-hand frame with ts - 1160 >= 600
        kinds = [type(e).__name__ for _, e in ev]
        self.assertEqual(kinds, ["SignSegment", "WordGap"])
        self.assertGreater(g[0].seq, segments(ev)[0].seq)

    def test_s6_no_word_gap_without_a_sign(self):
        frames = [(0.0, hand_at(0.3), "Left"), (40.0, hand_at(0.3), "Left")]  # 2 hand frames < min
        frames += [((2 + k) * 40.0, None, "") for k in range(60)]
        ev = run(new_seg(), frames)
        self.assertEqual(ev, [])

    def test_s6_second_word_needs_a_new_sign(self):
        f1, _ = move_then_still(10, 20)
        absent = [((30 + k) * 40.0, None, "") for k in range(30)]   # gap 1
        back = [((60 + k) * 40.0, hand_at(0.3), "Left") for k in range(2)]  # too short for a sign
        absent2 = [((62 + k) * 40.0, None, "") for k in range(30)]
        ev = run(new_seg(), f1 + absent + back + absent2)
        self.assertEqual(len(gaps(ev)), 1)

    def test_s7_small_jitter_is_still(self):
        frames, y = move_then_still(10, 0)
        for k in range(20):
            frames.append(((10 + k) * 40.0, hand_at(y, jitter=0.001 if k % 2 == 0 else -0.001), "Left"))
        segs = segments(run(new_seg(), frames))
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].close_reason, "hold")
        self.assertEqual(segs[0].t_emit_ms, 800.0)

    def test_s8_irregular_timestamps(self):
        def position(t):  # same motion in time: moving for t < 400 ms, then still
            return 0.3 + SPEED * min(t, 400.0) / 1000.0

        regular = [k * 40.0 for k in range(40)]
        steps = [30.0, 50.0, 45.0, 35.0]
        irregular = [0.0]
        while irregular[-1] < regular[-1]:
            irregular.append(irregular[-1] + steps[len(irregular) % 4])
        out = []
        for grid in (regular, irregular):
            frames = [(t, hand_at(position(t)), "Left") for t in grid]
            out.append(segments(run(new_seg(), frames)))
        self.assertEqual(len(out[0]), len(out[1]))
        self.assertEqual(len(out[0]), 1)
        max_interval = max(max(np.diff(regular)), max(np.diff(irregular)))
        self.assertLessEqual(abs(out[0][0].t_emit_ms - out[1][0].t_emit_ms), max_interval)

    def test_s9_buffer_limited_to_max_segment(self):
        frames, _ = move_then_still(125, 20)  # 5 s of motion (> max_segment 3 s), then hold
        segs = segments(run(new_seg(), frames))
        self.assertEqual(len(segs), 1)
        s = segs[0]
        self.assertLessEqual(s.t_end_ms - s.t_start_ms, PARAMS["max_segment_ms"])
        self.assertGreater(s.t_start_ms, 0.0)

    def test_s10_single_hand_frame_and_bad_timestamps(self):
        seg = new_seg()
        self.assertEqual(seg.push(0.0, hand_at(0.3), "Left", W, H), [])
        self.assertIsNone(seg.motion)
        self.assertEqual(seg.status()["state"], "moving")  # hand present, not still (M = None is not still)
        self.assertEqual(seg.push(40.0, None, "", W, H), [])
        self.assertEqual(seg.push(80.0, hand_at(0.3), "Left", W, H), [])  # no consecutive pair -> M = None
        self.assertIsNone(seg.motion)
        with self.assertRaises(ValueError):
            seg.push(80.0, hand_at(0.3), "Left", W, H)
        with self.assertRaises(ValueError):
            seg.push(60.0, hand_at(0.3), "Left", W, H)

    def test_s11_segment_content_is_a_copy_of_pushed_frames(self):
        frames, _ = move_then_still(10, 20)
        labels = ["Left", "Right"]
        frames = [(ts, lm, labels[i % 3 == 0]) for i, (ts, lm, _) in enumerate(frames)]
        seg = new_seg()
        pushed = []
        got = []
        for ts, lm, hd in frames:
            pushed.append((ts, lm.copy(), hd))
            got += seg.push(ts, lm, hd, W, H)
            lm[:] = 7.0  # the caller reusing its array must not change the buffer
        segs = [e for e in got if isinstance(e, SignSegment)]
        self.assertEqual(len(segs), 1)
        s = segs[0]
        n = s.n_frames
        self.assertTrue(np.array_equal(s.raw_landmarks, np.stack([p[1] for p in pushed[:n]])))
        self.assertEqual(s.raw_landmarks.dtype, np.float32)
        self.assertTrue(np.array_equal(s.detected, np.ones(n, dtype=bool)))
        self.assertEqual(list(s.handedness), [p[2] for p in pushed[:n]])
        self.assertTrue(np.array_equal(s.timestamps_ms, np.array([p[0] for p in pushed[:n]])))
        self.assertEqual((s.frame_width, s.frame_height), (W, H))
        # copy: changing the segment changes neither the segmenter's buffer nor a later segment
        for f in seg._buf:
            self.assertFalse(np.shares_memory(s.raw_landmarks, f[0]))
        before = [f[0].copy() for f in seg._buf]
        s.raw_landmarks[:] = -1.0
        s.detected[:] = False
        self.assertTrue(all(np.array_equal(a, f[0]) for a, f in zip(before, seg._buf)))

    def test_s11_hand_lost_segment_with_inner_gap(self):
        frames, _ = move_then_still(6, 0)
        frames.append((6 * 40.0, None, ""))  # one missed detection inside the sign
        more, _ = move_then_still(6, 0, y0=0.5, start_index=7)
        frames += more
        frames += [((13 + k) * 40.0, None, "") for k in range(8)]
        segs = segments(run(new_seg(), frames))
        self.assertEqual(len(segs), 1)
        s = segs[0]
        self.assertEqual(s.n_frames, 13)
        self.assertEqual(list(s.detected), [True] * 6 + [False] + [True] * 6)
        self.assertTrue(np.array_equal(s.raw_landmarks[6], np.zeros((21, 3), dtype=np.float32)))
        self.assertEqual(s.handedness[6], "")

    def test_s12_too_few_hand_frames(self):
        seg = Level1SignSegmenter({**PARAMS, "min_sign_frames": 10}, MIN_DETECTED)
        frames = [(k * 100.0, hand_at(0.3), "Left") for k in range(9)]  # still, held 700 ms, 9 hand frames
        frames += [((9 + k) * 100.0, None, "") for k in range(12)]
        ev = run(seg, frames)
        self.assertEqual(ev, [])
        self.assertEqual(seg.flush(2200.0), [])
        # the checkpoint's min_detected_frames wins when larger
        self.assertEqual(Level1SignSegmenter({**PARAMS, "min_sign_frames": 2}, 5).min_frames, 5)

    def test_s13_flush_end_of_stream(self):
        frames, _ = move_then_still(12, 0)
        seg = new_seg()
        self.assertEqual(segments(run(seg, frames)), [])
        out = seg.flush(12 * 40.0)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].close_reason, "end_of_stream")
        self.assertEqual(out[0].n_frames, 12)
        self.assertEqual(seg.flush(13 * 40.0), [])

    def test_s14_tail_still_keep_ms_equal_hold_ms(self):
        # On S1:
        frames_s1, _ = move_then_still(10, 20)
        ev_base = run(new_seg(tail_still_keep_ms=400), frames_s1)
        segs_base = segments(ev_base)
        self.assertEqual(len(segs_base), 1)
        self.assertEqual(segs_base[0].close_reason, "hold")
        self.assertEqual(segs_base[0].t_start_ms, 0.0)
        self.assertEqual(segs_base[0].t_end_ms, 800.0)
        self.assertEqual(segs_base[0].t_emit_ms, 800.0)
        self.assertEqual(segs_base[0].n_frames, 21)

        # On S3:
        f1, y = move_then_still(10, 20)
        f2, _ = move_then_still(10, 30, y0=y + SPEED * 0.04, start_index=30)
        ev_s3 = run(new_seg(tail_still_keep_ms=400), f1 + f2)
        segs_s3 = segments(ev_s3)
        self.assertEqual(len(segs_s3), 2)
        self.assertEqual([s.close_reason for s in segs_s3], ["hold", "hold"])
        self.assertEqual(segs_s3[1].t_start_ms, 1200.0)
        self.assertEqual(segs_s3[1].t_end_ms, 2000.0)
        self.assertEqual(segs_s3[1].t_emit_ms, 2000.0)

    def test_s15_tail_still_keep_ms_less_than_hold_ms(self):
        # hold_ms = 400, tail_still_keep_ms = 200 (< hold_ms)
        frames, _ = move_then_still(10, 20)
        ev = run(new_seg(hold_ms=400, tail_still_keep_ms=200), frames)
        segs = segments(ev)
        self.assertEqual(len(segs), 1)
        s = segs[0]
        self.assertEqual(s.close_reason, "hold")
        self.assertEqual(s.t_emit_ms, 800.0)  # t_emit unchanged!
        self.assertLessEqual(s.t_end_ms, 600.0)  # ts <= _still_since + tail_still_keep_ms
        self.assertEqual(s.t_end_ms, 600.0)
        self.assertEqual(s.n_frames, 16)
        self.assertEqual(s.t_start_ms, 0.0)

    def test_parameter_checks(self):
        with self.assertRaises(ValueError):
            Level1SignSegmenter({k: v for k, v in PARAMS.items() if k != "hold_ms"}, MIN_DETECTED)
        with self.assertRaises(ValueError):
            Level1SignSegmenter({k: v for k, v in PARAMS.items() if k != "tail_still_keep_ms"}, MIN_DETECTED)
        with self.assertRaises(ValueError):
            Level1SignSegmenter({**PARAMS, "move_speed": 1.0}, MIN_DETECTED)
        with self.assertRaises(ValueError):
            Level1SignSegmenter({**PARAMS, "word_gap_ms": 100}, MIN_DETECTED)
        with self.assertRaises(ValueError):
            Level1SignSegmenter({**PARAMS, "tail_still_keep_ms": 0}, MIN_DETECTED)
        with self.assertRaises(ValueError):
            Level1SignSegmenter({**PARAMS, "tail_still_keep_ms": -50}, MIN_DETECTED)
        with self.assertRaises(ValueError):
            Level1SignSegmenter({**PARAMS, "tail_still_keep_ms": 500}, MIN_DETECTED)  # > hold_ms (400)

    def test_hud_status(self):
        frames, _ = move_then_still(10, 15)
        seg = new_seg()
        run(seg, frames[:10])
        self.assertEqual(seg.status()["state"], "moving")
        run(seg, [(f[0], f[1], f[2]) for f in frames[10:15]])
        st = seg.status()
        self.assertEqual(st["state"], "holding")
        self.assertTrue(st["armed"])
        self.assertGreater(st["hold_progress"], 0.0)
        self.assertLess(st["hold_progress"], 1.0)


# ------------------------------------------------------------------ plan 15 lần sửa 2 §4: AC-S16 / AC-S17 / AC-S18
REF_COMMIT = "4a55bf0"          # segmenter before tail_still_keep_ms ("no filtering" reference, plan 15 lần sửa 2 §4)
BEFORE_CONFIG_COMMIT = "3ebc7b9"  # config before A2 (AC-S18 config (b))


def _git_show(spec):
    """`git show <spec>` as text; a missing commit (shallow clone) FAILS the caller, it is never skipped."""
    import subprocess
    r = subprocess.run(["git", "show", spec], cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError(f"git show {spec} failed (missing commit / shallow clone?): {r.stderr.strip()}")
    return r.stdout


_REF_MODULE = None


def reference_segmenter_module():
    """The segmenter at REF_COMMIT loaded from `git show` into a temporary in-memory module (nothing is written to
    the repo; the module is removed from sys.modules after loading)."""
    global _REF_MODULE
    if _REF_MODULE is None:
        import types
        src = _git_show(f"{REF_COMMIT}:src/inference/level1_segmenter.py")
        name = f"_level1_segmenter_ref_{REF_COMMIT}"
        mod = types.ModuleType(name)
        mod.__file__ = f"<git show {REF_COMMIT}:src/inference/level1_segmenter.py>"
        sys.modules[name] = mod  # dataclass processing looks the module up while the class body runs
        try:
            exec(compile(src, mod.__file__, "exec"), mod.__dict__)
        finally:
            sys.modules.pop(name, None)
        _REF_MODULE = mod
    return _REF_MODULE


def run_detail(seg, frames):
    """Like run(), also returns seg._still_since right after each frame that emitted a 'hold' segment."""
    out, still_at_emit = [], {}
    for i, (ts, lm, hd) in enumerate(frames):
        evs = seg.push(ts, lm, hd if lm is not None else "", W, H)
        for ev in evs:
            out.append((i, ev))
            if isinstance(ev, SignSegment) and ev.close_reason == "hold":
                still_at_emit[ev.seq] = seg._still_since
    return out, still_at_emit


def irregular_grid_33_47(t_max):
    """Timestamps with dt alternating 33 / 47 ms."""
    ts = [0.0]
    while ts[-1] < t_max:
        ts.append(ts[-1] + (33.0 if len(ts) % 2 else 47.0))
    return ts


def fps_grid(t_max, fps=23.584):
    """Real-fps grid i * 1000 / fps (hauuto fps)."""
    ts, i = [], 0
    while not ts or ts[-1] < t_max:
        ts.append(i * 1000.0 / fps)
        i += 1
    return ts


# two signs: moving [0, 400) -> still [400, 1300) -> moving [1300, 1700) -> still [1700, 2600]
PHASES = ((0.0, 400.0, True), (400.0, 1300.0, False), (1300.0, 1700.0, True), (1700.0, 2600.0, False))
STILL_STARTS = (400.0, 1700.0)  # the times at which the test makes the hand stop
T_MAX = PHASES[-1][1]


def phase_position(t, y0=0.3):
    """Wrist y at time t: moves at SPEED during the moving phases, stays during the still phases."""
    moved = 0.0
    for a, b, moving in PHASES:
        if moving:
            moved += max(0.0, min(t, b) - a)
    return y0 + SPEED * moved / 1000.0


def phase_frames(grid):
    return [(t, hand_at(phase_position(t)), "Left") for t in grid]


def assert_events_identical(tc, got, ref, where):
    tc.assertEqual(len(got), len(ref), f"{where}: number of events")
    for k, ((_, a), (_, b)) in enumerate(zip(got, ref)):
        tc.assertEqual(type(a).__name__, type(b).__name__, f"{where}: event {k} type")
        if type(a).__name__ == "WordGap":
            tc.assertEqual((a.seq, a.t_ms), (b.seq, b.t_ms), f"{where}: event {k}")
            continue
        tc.assertTrue(np.array_equal(a.raw_landmarks, b.raw_landmarks), f"{where}: event {k} raw_landmarks")
        tc.assertEqual(a.raw_landmarks.dtype, b.raw_landmarks.dtype, f"{where}: event {k} raw dtype")
        tc.assertTrue(np.array_equal(a.detected, b.detected), f"{where}: event {k} detected")
        tc.assertTrue(np.array_equal(a.handedness, b.handedness), f"{where}: event {k} handedness")
        tc.assertTrue(np.array_equal(a.timestamps_ms, b.timestamps_ms), f"{where}: event {k} timestamps_ms")
        tc.assertEqual((a.seq, a.close_reason, a.t_start_ms, a.t_end_ms, a.t_emit_ms, a.frame_width,
                        a.frame_height),
                       (b.seq, b.close_reason, b.t_start_ms, b.t_end_ms, b.t_emit_ms, b.frame_width,
                        b.frame_height), f"{where}: event {k} fields")


HOLD_S16 = 390.0  # with dt 33/47 (pairs of 80 ms) and dt 42.40 ms no hand-held time lands exactly on 390 ms


class TestTailIrregularS16S17(unittest.TestCase):
    """AC-S16 / AC-S17 (plan 15 lần sửa 2 §4): uneven frame intervals, emit frame with held > hold_ms."""

    GRIDS = {"dt_33_47": irregular_grid_33_47(T_MAX), "fps_23.584": fps_grid(T_MAX)}

    def _params(self, tail):
        return {**PARAMS, "hold_ms": HOLD_S16, "tail_still_keep_ms": tail}

    def test_s16_irregular_tail_equal_hold_identical_to_reference(self):
        ref_mod = reference_segmenter_module()
        for name, grid in self.GRIDS.items():
            with self.subTest(grid=name):
                frames = phase_frames(grid)
                p = self._params(HOLD_S16)
                got, still_at = run_detail(Level1SignSegmenter(p, MIN_DETECTED), frames)
                ref = run(ref_mod.Level1SignSegmenter(p, MIN_DETECTED), frames)
                holds = [e for _, e in got if isinstance(e, SignSegment) and e.close_reason == "hold"]
                self.assertEqual(len(holds), 2, name)
                for s in holds:
                    held = s.t_emit_ms - still_at[s.seq]
                    self.assertGreater(held, p["hold_ms"], f"{name}: the emit frame must have held > hold_ms")
                    self.assertEqual(s.t_end_ms, s.t_emit_ms, name)
                    n_hand = sum(1 for ts, lm, _ in frames if lm is not None and s.t_start_ms <= ts <= s.t_emit_ms)
                    self.assertEqual(s.n_frames, n_hand, name)
                assert_events_identical(self, got, ref, name)

    def test_s17_irregular_tail_half_hold_prefix_and_cut(self):
        for name, grid in self.GRIDS.items():
            with self.subTest(grid=name):
                frames = phase_frames(grid)
                ts_all = [f[0] for f in frames]
                max_dt = float(max(np.diff(ts_all)))
                full = segments(run(Level1SignSegmenter(self._params(HOLD_S16), MIN_DETECTED), frames))
                tail = HOLD_S16 / 2.0
                half = segments(run(Level1SignSegmenter(self._params(tail), MIN_DETECTED), frames))
                self.assertEqual(len(half), len(full), name)
                self.assertEqual(len(half), 2, name)
                for k, (h, f) in enumerate(zip(half, full)):
                    self.assertEqual(h.close_reason, "hold", name)
                    self.assertEqual(h.t_emit_ms, f.t_emit_ms, f"{name}: t_emit unchanged")
                    n = h.n_frames
                    self.assertLessEqual(n, f.n_frames, name)
                    self.assertEqual(h.t_start_ms, f.t_start_ms, name)
                    self.assertTrue(np.array_equal(h.raw_landmarks, f.raw_landmarks[:n]), f"{name}: prefix raw")
                    self.assertTrue(np.array_equal(h.detected, f.detected[:n]), f"{name}: prefix detected")
                    self.assertTrue(np.array_equal(h.handedness, f.handedness[:n]), f"{name}: prefix handedness")
                    self.assertTrue(np.array_equal(h.timestamps_ms, f.timestamps_ms[:n]), f"{name}: prefix ts")
                    cutoff = h.t_emit_ms - (HOLD_S16 - tail)
                    self.assertLessEqual(h.t_end_ms, cutoff, name)
                    i_end = ts_all.index(h.t_end_ms)
                    if i_end + 1 < len(frames) and frames[i_end + 1][1] is not None:
                        self.assertGreater(ts_all[i_end + 1], cutoff, f"{name}: cut no more than needed")
                    self.assertGreaterEqual(h.t_end_ms - STILL_STARTS[k], tail - max_dt, name)


# ------------------------------------------------------------------ AC-S18 (real hauuto clips)
CURRENT_CONFIG = os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json")


def s18_configs():
    """AC-S18 configs: name -> config values. (a) configs/level1_realtime.json; (b) the config at
    BEFORE_CONFIG_COMMIT with tail_still_keep_ms = hold_ms (that config predates the key)."""
    import json
    from src.inference.level1_core import load_level1_config
    cur = dict(load_level1_config(CURRENT_CONFIG)["values"])
    raw = json.loads(_git_show(f"{BEFORE_CONFIG_COMMIT}:configs/level1_realtime.json"))
    before = {k: v["value"] for k, v in raw.items() if isinstance(v, dict) and "value" in v}
    if "tail_still_keep_ms" in before:
        raise AssertionError(f"config at {BEFORE_CONFIG_COMMIT} already has tail_still_keep_ms")
    before["tail_still_keep_ms"] = before["hold_ms"]
    # plan 15 lần sửa 3 §0: AC-S18 runs with the pose rules off for both configs (keys filled, assertions unchanged)
    cur["pose_change_rules"] = False
    before.update({"pose_change_rules": False, "rearm_pose_dist": cur["rearm_pose_dist"],
                   "pose_over_jitter_ratio": cur["pose_over_jitter_ratio"]})
    return {"a_current": cur, "b_before_3ebc7b9_tail_eq_hold": before}


def run_clip(seg_cls, params, clip, timestamps):
    """One fresh segmenter per clip, every frame pushed, flush 1 ms after the last frame (as boundary_check.py)."""
    seg = seg_cls(params, int(params["min_sign_frames"]))
    evs = []
    for i, t in enumerate(timestamps):
        det = bool(clip["detected"][i])
        evs += seg.push(float(t), clip["raw"][i] if det else None, clip["handedness"][i] if det else "",
                        clip["width"], clip["height"])
    evs += seg.flush(float(timestamps[-1]) + 1.0)
    return [(None, e) for e in evs]


class TestRealClipsS18(unittest.TestCase):
    """AC-S18 (plan 15 lần sửa 2 §4): every hauuto clip of the manifest, HEAD segmenter == segmenter at 4a55bf0.
    Behaviour-equivalence check on the train clips of the checkpoint; not accuracy. No skip: missing data or a
    missing commit fails."""

    def test_s18_all_hauuto_clips_identical_to_reference(self):
        import csv
        from scripts.level1_segment_report import MANIFEST, clip_timestamps, load_train_clips
        with open(MANIFEST, encoding="utf-8") as f:
            n_rows = sum(1 for r in csv.DictReader(f) if r["source"] == "hauuto")
        data = load_train_clips(MANIFEST, 0)  # 0: no clip is dropped here
        self.assertEqual(data["excluded"], [])
        self.assertEqual(len(data["clips"]), n_rows)
        self.assertEqual(data["n_manifest_hauuto"], n_rows)
        self.assertGreater(n_rows, 0)
        ref_mod = reference_segmenter_module()
        for cfg_name, values in s18_configs().items():
            self.assertEqual(values["tail_still_keep_ms"], values["hold_ms"], cfg_name)
            n_clips = 0
            for clip in data["clips"]:
                ts = clip_timestamps(len(clip["detected"]), clip["fps"])
                got = run_clip(Level1SignSegmenter, values, clip, ts)
                ref = run_clip(ref_mod.Level1SignSegmenter, values, clip, ts)
                assert_events_identical(self, got, ref, f"{cfg_name}/{clip['sample_id']}")
                n_clips += 1
            self.assertEqual(n_clips, n_rows, cfg_name)

    def test_s18b_rearm_pose_dist_unused_when_rules_off(self):
        """plan 15 lần sửa 3 §0: with pose_change_rules false two different rearm_pose_dist values give identical
        events on every hauuto clip (the key is not read when the rules are off)."""
        import csv
        from scripts.level1_segment_report import MANIFEST, clip_timestamps, load_train_clips
        with open(MANIFEST, encoding="utf-8") as f:
            n_rows = sum(1 for r in csv.DictReader(f) if r["source"] == "hauuto")
        data = load_train_clips(MANIFEST, 0)
        self.assertEqual(len(data["clips"]), n_rows)
        for cfg_name, values in s18_configs().items():
            self.assertIs(values["pose_change_rules"], False, cfg_name)
            other = {**values, "rearm_pose_dist": values["rearm_pose_dist"] * 0.01}
            for clip in data["clips"]:
                ts = clip_timestamps(len(clip["detected"]), clip["fps"])
                assert_events_identical(self, run_clip(Level1SignSegmenter, values, clip, ts),
                                        run_clip(Level1SignSegmenter, other, clip, ts),
                                        f"{cfg_name}/{clip['sample_id']}")



# ------------------------------------------------------------------ plan 15 lần sửa 4 §3.1 / §5: AC-K1 / AC-K2 / AC-K4 (key n "chữ kế")
BEFORE_K1_COMMIT = "5c62d13"  # segmenter before force_rearm (AC-K4 reference)
_BEFORE_K1_MODULE = None


def before_k1_segmenter_module():
    """The segmenter at BEFORE_K1_COMMIT loaded from `git show` into a temporary in-memory module (as
    reference_segmenter_module; nothing is written to the repo)."""
    global _BEFORE_K1_MODULE
    if _BEFORE_K1_MODULE is None:
        import types
        src = _git_show(f"{BEFORE_K1_COMMIT}:src/inference/level1_segmenter.py")
        name = f"_level1_segmenter_ref_{BEFORE_K1_COMMIT}"
        mod = types.ModuleType(name)
        mod.__file__ = f"<git show {BEFORE_K1_COMMIT}:src/inference/level1_segmenter.py>"
        sys.modules[name] = mod
        try:
            exec(compile(src, mod.__file__, "exec"), mod.__dict__)
        finally:
            sys.modules.pop(name, None)
        _BEFORE_K1_MODULE = mod
    return _BEFORE_K1_MODULE


class TestForceRearmK1K2(unittest.TestCase):
    """AC-K1 / AC-K2 (plan 15 lần sửa 4 §5): Level1SignSegmenter.force_rearm on a controlled landmark sequence built
    in this test (chuỗi landmark tạo có kiểm soát để kiểm logic, không phải dữ liệu thật)."""

    def _push(self, seg, frames, start=0):
        out = []
        for i, (ts, lm, hd) in enumerate(frames, start=start):
            for ev in seg.push(ts, lm, hd if lm is not None else "", W, H):
                out.append((i, ev))
        return out

    def test_k1_hold_force_rearm_hold_two_segments(self):
        """Hold A -> 'hold' -> force_rearm -> keep holding A >= hold_ms -> exactly 2 'hold' segments; segment 2 only
        has frames with ts >= the key press."""
        frames, y = move_then_still(10, 20)            # frames 0..29, first 'hold' at frame 20 (800 ms)
        more = [((30 + k) * 40.0, hand_at(y), "Left") for k in range(30)]  # frames 30..59, still at the same place
        seg = new_seg()
        ev = self._push(seg, frames)
        self.assertEqual([e.close_reason for e in segments(ev)], ["hold"])
        self.assertFalse(seg.armed)
        press = frames[-1][0]                           # key pressed after frame 29 (t = 1160 ms)
        self.assertIsNone(seg.force_rearm(press))       # emits nothing itself
        self.assertTrue(seg.armed)
        ev2 = self._push(seg, more, start=30)
        segs2 = segments(ev2)
        self.assertEqual([s.close_reason for s in segs2], ["hold"])
        s2 = segs2[0]
        self.assertTrue(np.all(s2.timestamps_ms >= press))
        self.assertEqual(s2.t_start_ms, press)          # the last frame before the key has ts == press and is kept
        # the hold clock restarted at the key press: first frame with held >= hold_ms
        self.assertEqual(s2.t_emit_ms, press + PARAMS["hold_ms"])
        # holding on: no third segment
        ev3 = self._push(seg, [((60 + k) * 40.0, hand_at(y), "Left") for k in range(30)], start=60)
        self.assertEqual(segments(ev3), [])

    def test_k1_moving_buffer_cut_without_still_clock(self):
        """force_rearm while moving (hold clock not running): buffer cut to ts >= press, no hold clock invented."""
        seg = new_seg()
        f1, y = move_then_still(10, 0)                  # frames 0..9 moving, armed (first hand), no segment
        self.assertEqual(segments(self._push(seg, f1)), [])
        press = f1[5][0] + 1.0                          # between frames 5 and 6 (key pressed late)
        seg.force_rearm(press)
        self.assertIsNone(seg._still_since)
        f2 = [((10 + k) * 40.0, hand_at(y), "Left") for k in range(20)]
        s = segments(self._push(seg, f2, start=10))
        self.assertEqual(len(s), 1)
        self.assertGreaterEqual(float(s[0].timestamps_ms.min()), press)

    def test_k2_force_rearm_while_armed_adds_no_segment(self):
        """Already armed: force_rearm only resets the buffer / hold clock, no extra segment."""
        frames, y = move_then_still(10, 20)
        ref = segments(run(new_seg(), frames))
        self.assertEqual(len(ref), 1)
        seg = new_seg()
        ev = self._push(seg, frames[:15])               # armed, still since 400 ms, hold not reached (600 ms)
        self.assertTrue(seg.armed)
        seg.force_rearm(frames[14][0])
        self.assertTrue(seg.armed)
        ev += self._push(seg, frames[15:] + [((30 + k) * 40.0, hand_at(y), "Left") for k in range(20)], start=15)
        segs = segments(ev)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].t_start_ms, frames[14][0])
        self.assertEqual(segs[0].t_emit_ms, frames[14][0] + PARAMS["hold_ms"])

    def test_k2_force_rearm_without_hand_is_a_no_op(self):
        seg = new_seg()
        self.assertEqual(seg.push(0.0, None, "", W, H), [])
        seg.force_rearm(10.0)
        self.assertFalse(seg.armed)
        self.assertEqual(seg.state, "no_hand")
        with self.assertRaises(ValueError):
            new_seg().force_rearm(float("nan"))


class TestNoKeyIdenticalK4(unittest.TestCase):
    """AC-K4 (plan 15 lần sửa 4 §5): without the key, the segmenter after K1 gives events identical (array_equal) to
    the segmenter at BEFORE_K1_COMMIT on the streams of AC-S1…S18 (controlled sequences of this file + every hauuto
    clip of the manifest with both AC-S18 configs). A missing commit or missing data fails, it is never skipped."""

    def _controlled_streams(self):
        streams = {}
        f1, y = move_then_still(10, 20)
        f2, _ = move_then_still(10, 30, y0=y + SPEED * 0.04, start_index=30)
        streams["s1"] = f1
        streams["s2"] = move_then_still(10, 100)[0]
        streams["s3"] = f1 + f2
        streams["s4"] = f1 + move_then_still(2, 38, y0=y + SPEED * 0.04, start_index=30)[0]
        s5, _ = move_then_still(15, 0)
        streams["s5"] = s5 + [((15 + k) * 40.0, None, "") for k in range(10)]
        streams["s6"] = f1 + [((30 + k) * 40.0, None, "") for k in range(30)] + \
            [(f[0] + 2400.0, f[1], f[2]) for f in f1]
        for name, grid in TestTailIrregularS16S17.GRIDS.items():
            streams[f"s16_{name}"] = phase_frames(grid)
        return streams

    def test_k4_controlled_streams_identical(self):
        ref_mod = before_k1_segmenter_module()
        for p_name, p in (("params", PARAMS), ("params_tail_half", {**PARAMS, "tail_still_keep_ms": 200}),
                          ("params_rules_on", {**PARAMS, "pose_change_rules": True})):
            for name, frames in self._controlled_streams().items():
                with self.subTest(params=p_name, stream=name):
                    got = run(Level1SignSegmenter(p, MIN_DETECTED), frames)
                    ref = run(ref_mod.Level1SignSegmenter(p, MIN_DETECTED), frames)
                    assert_events_identical(self, got, ref, f"{p_name}/{name}")

    def test_k4_all_hauuto_clips_identical(self):
        import csv
        from scripts.level1_segment_report import MANIFEST, clip_timestamps, load_train_clips
        with open(MANIFEST, encoding="utf-8") as f:
            n_rows = sum(1 for r in csv.DictReader(f) if r["source"] == "hauuto")
        data = load_train_clips(MANIFEST, 0)
        self.assertEqual(len(data["clips"]), n_rows)
        self.assertGreater(n_rows, 0)
        ref_mod = before_k1_segmenter_module()
        for cfg_name, values in s18_configs().items():
            for clip in data["clips"]:
                ts = clip_timestamps(len(clip["detected"]), clip["fps"])
                assert_events_identical(self, run_clip(Level1SignSegmenter, values, clip, ts),
                                        run_clip(ref_mod.Level1SignSegmenter, values, clip, ts),
                                        f"{cfg_name}/{clip['sample_id']}")


if __name__ == "__main__":
    unittest.main()
