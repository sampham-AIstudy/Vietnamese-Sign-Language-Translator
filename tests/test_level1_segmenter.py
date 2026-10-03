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
          "tail_still_keep_ms": 400}
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


if __name__ == "__main__":
    unittest.main()
