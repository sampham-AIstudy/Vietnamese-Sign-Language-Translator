"""
Plan 04 AC1: src/inference/sign_segmenter.py (pure-numpy sign segmenter of the live "Ký từ" path).

Landmarks below are FIXTURES generated in the test (like tests/test_harmonized.py::clip), not data:
shoulders at y=0.4 (width 0.2 on a square frame), left hand resting at the hip, right hand moved by a
per-frame height profile. On a square frame the normalised wrist height is (y - 0.4) / 0.2 shoulder widths,
so y=0.75 (1.75, at the hip) is rest and y=0.45 (0.25) is a raised hand.
"""
import os
import subprocess
import sys
import unittest

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.data.harmonized import HARMONIZED_DEFAULT, _normalise, active_span, hand_activity  # noqa: E402
from src.inference.sign_segmenter import SEGMENTER_DEFAULT, Discard, Emit, SignSegmenter  # noqa: E402

CKPT_CFG = {k: HARMONIZED_DEFAULT[k] for k in ("rest_y", "active_speed", "pad_s", "max_gap_s", "mask_resting_hand")}
SQUARE = (480, 480)
REST_Y, UP_Y = 0.75, 0.45
_HAND = np.random.default_rng(0).normal(0, 0.01, (21, 3)).astype(np.float32)   # fixed hand shape (fixture)


def frame(y_right, right_visible=True, left_visible=True, x_right=0.4):
    """One fixture frame: coords [67,3] (NaN = missing), vis [67]."""
    k = np.full((67, 3), np.nan, np.float32)
    v = np.zeros(67, np.float32)
    k[:25] = 0.5
    k[:25, 2] = 0.0
    v[:25] = 1
    k[11, :2], k[12, :2] = [0.6, 0.4], [0.4, 0.4]
    k[13, :2], k[14, :2] = [0.62, 0.55], [0.38, 0.55]
    k[15, :2], k[16, :2] = [0.62, 0.7], [0.38, 0.7]
    k[23, :2], k[24, :2] = [0.58, 0.7], [0.42, 0.7]
    if left_visible:
        k[25:46] = _HAND + [0.6, REST_Y, 0.0]
        v[25:46] = 1
    if right_visible:
        k[46:67] = _HAND + [x_right, y_right, 0.0]
        v[46:67] = 1
    return k, v


def sign_profile(t, start, end, ramp=0.2):
    """Right-hand height: rest -> raised over `ramp` s -> small side motion -> back to rest."""
    if t < start or t > end:
        return REST_Y
    up = min(1.0, (t - start) / ramp, (end - t) / ramp)
    return REST_Y - (REST_Y - UP_Y) * max(0.0, up)


def build(times, y_of_t, **kw):
    """Side motion of the right hand only while it is raised (a resting hand is still)."""
    def x_of(t):
        up = (REST_Y - y_of_t(t)) / (REST_Y - UP_Y)
        return 0.4 + 0.03 * np.sin(2 * np.pi * t) * max(0.0, min(1.0, up))
    ks, vs = zip(*[frame(y_of_t(t), x_right=x_of(t), **kw) for t in times])
    return np.stack(ks), np.stack(vs)


def feed(seg, times, kps, vis, wh=SQUARE):
    """Push every frame; returns [(index, event)] and the state after each push."""
    events, states = [], []
    for i, t in enumerate(times):
        ev = seg.push(kps[i], vis[i], t, wh)
        if ev is not None:
            events.append((i, ev))
        states.append(seg.state)
    return events, states


def offline_activity(kps, vis, fps, cfg=CKPT_CFG, aspect=1.0):
    kn, vn = _normalise(kps, vis, aspect)
    left, right = hand_activity(kn, vn, fps, cfg)
    return left | right, active_span(kn, vn, fps, cfg)


class TestSignSegmenter(unittest.TestCase):
    fps = 30.0

    def times(self, dur, fps=None):
        fps = fps or self.fps
        return np.arange(int(round(dur * fps))) / fps

    def test_a_rest_only_no_event(self):
        t = self.times(5.0)
        for kw in ({}, {"right_visible": False, "left_visible": False}):
            with self.subTest(**kw):
                k, v = build(t, lambda _: REST_Y, **kw)
                seg = SignSegmenter(CKPT_CFG)
                events, states = feed(seg, t, k, v)
                self.assertEqual(events, [])
                self.assertEqual(set(states), {"idle"})

    def test_b_one_sign_one_emit_contains_offline_span(self):
        t = self.times(3.5)
        k, v = build(t, lambda x: sign_profile(x, 1.0, 2.5))
        seg = SignSegmenter(CKPT_CFG)
        events, _ = feed(seg, t, k, v)
        self.assertEqual(len(events), 1)
        i_ev, ev = events[0]
        self.assertIsInstance(ev, Emit)
        act, (a, b) = offline_activity(k, v, self.fps)
        self.assertLessEqual(ev.t[0], t[a])
        self.assertGreaterEqual(ev.t[-1], t[b - 1])
        last_active = np.flatnonzero(act)[-1]
        expected = next(i for i in range(len(t)) if i > last_active and t[i] - t[last_active] >= SEGMENTER_DEFAULT["rest_hold_s"])
        self.assertEqual(i_ev, expected)
        self.assertEqual(ev.t[-1], t[i_ev])
        self.assertEqual(ev.kps.shape, (len(ev.t), 67, 3))
        self.assertEqual(ev.frame_wh, SQUARE)
        self.assertEqual(ev.active_end_s, t[last_active])

    def test_c_two_signs_two_emits_increasing_ids(self):
        t = self.times(6.0)
        k, v = build(t, lambda x: sign_profile(x, 0.8, 2.0) if x < 3.0 else sign_profile(x, 3.6, 4.8))
        seg = SignSegmenter(CKPT_CFG)
        events, _ = feed(seg, t, k, v)
        self.assertEqual([type(e) for _, e in events], [Emit, Emit])
        self.assertEqual([e.segment_id for _, e in events], [1, 2])
        self.assertLess(events[0][1].t[-1], events[1][1].t[0] + 1e-9)

    def test_d_hand_up_too_long_then_wait_rest(self):
        t = self.times(12.0)
        k, v = build(t, lambda x: UP_Y if 0.5 <= x < 10.5 else REST_Y)
        seg = SignSegmenter(CKPT_CFG)
        events, states = feed(seg, t, k, v)
        act, _ = offline_activity(k, v, self.fps)
        onset = t[np.flatnonzero(act)[0]]
        self.assertEqual(len(events), 1)
        i_ev, ev = events[0]
        self.assertIsInstance(ev, Discard)
        self.assertEqual(ev.reason, "too_long")
        self.assertEqual(i_ev, next(i for i in range(len(t)) if t[i] - onset > SEGMENTER_DEFAULT["max_sign_s"]))
        self.assertEqual(states[i_ev], "wait_rest")
        last_up = int(np.flatnonzero(act)[-1])
        self.assertTrue(all(s == "wait_rest" for s in states[i_ev:last_up + 1]))
        self.assertEqual(states[-1], "idle")   # hand lowered >= rest_hold_s
        back = next(i for i in range(last_up + 1, len(t)) if t[i] - t[last_up + 1] >= SEGMENTER_DEFAULT["rest_hold_s"])
        self.assertEqual(states[back - 1], "wait_rest")
        self.assertEqual(states[back], "idle")

    def test_e_too_short(self):
        t = self.times(3.0)
        k, v = build(t, lambda x: UP_Y if 1.0 <= x < 1.2 else REST_Y)
        seg = SignSegmenter(CKPT_CFG)
        events, _ = feed(seg, t, k, v)
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0][1], Discard)
        self.assertEqual(events[0][1].reason, "too_short")

    def test_f_stream_gap(self):
        t = self.times(4.0)
        t = np.where(t >= 1.6, t + 1.5, t)          # 1.5 s jump while recording (> stream_gap_s)
        k, v = build(t, lambda x: sign_profile(x, 1.0, 5.0))
        seg = SignSegmenter(CKPT_CFG)
        events, states = feed(seg, t, k, v)
        gap_i = int(np.flatnonzero(np.diff(t) > 1.0)[0]) + 1
        self.assertEqual(states[gap_i - 1], "recording")
        first = events[0]
        self.assertEqual(first[0], gap_i)
        self.assertIsInstance(first[1], Discard)
        self.assertEqual(first[1].reason, "stream_gap")

    def test_g_frame_size_changed(self):
        t = self.times(3.0)
        k, v = build(t, lambda x: sign_profile(x, 1.0, 2.5))
        seg = SignSegmenter(CKPT_CFG)
        events = []
        for i, x in enumerate(t):
            wh = SQUARE if x < 1.6 else (640, 640)
            if x >= 1.6 and seg.state == "recording" and not events:
                ev = seg.push(k[i], v[i], x, wh)
                events.append(ev)
            else:
                seg.push(k[i], v[i], x, wh)
        self.assertIsInstance(events[0], Discard)
        self.assertEqual(events[0].reason, "frame_size_changed")
        self.assertIn(seg.state, ("idle", "recording"))

    def test_h_non_increasing_timestamp_rejected_without_change(self):
        t = self.times(2.0)
        k, v = build(t, lambda x: sign_profile(x, 0.5, 3.0))
        seg = SignSegmenter(CKPT_CFG)
        for stop in (5, len(t)):   # while idle, then while recording
            seg = SignSegmenter(CKPT_CFG)
            feed(seg, t[:stop], k[:stop], v[:stop])
            before = (seg.state, seg.n_frames, seg.segment_id, seg.recording_s, [r[2] for r in seg._buf])
            for bad in (t[stop - 1], t[stop - 1] - 0.01, float("nan")):
                with self.subTest(stop=stop, bad=bad), self.assertRaises(ValueError):
                    seg.push(k[stop - 1], v[stop - 1], bad, SQUARE)
                after = (seg.state, seg.n_frames, seg.segment_id, seg.recording_s, [r[2] for r in seg._buf])
                self.assertEqual(before, after)
        self.assertEqual(seg.state, "recording")

    def test_i_parameters_come_from_the_checkpoint(self):
        t = self.times(3.0)
        y_mid = 0.4 + 1.2 * 0.2                      # wrist still at 1.2 shoulder widths below the shoulders
        k, v = build(t, lambda _: y_mid)
        k[:, 46:67, 0] = (_HAND[:, 0] + 0.4)[None]   # no side motion: position decides
        reached = {}
        for rest_y in (1.0, 1.4):
            seg = SignSegmenter({**CKPT_CFG, "rest_y": rest_y})
            _, states = feed(seg, t, k, v)
            reached[rest_y] = "recording" in states
        self.assertEqual(reached, {1.0: False, 1.4: True})
        for key in CKPT_CFG:
            with self.subTest(missing=key), self.assertRaises(ValueError):
                SignSegmenter({kk: vv for kk, vv in CKPT_CFG.items() if kk != key})

    def test_j_pre_roll(self):
        t = self.times(3.5)
        k, v = build(t, lambda x: sign_profile(x, 1.0, 2.5))
        ev = [e for _, e in feed(SignSegmenter(CKPT_CFG), t, k, v)[0]][0]
        self.assertLessEqual(ev.t[0], ev.active_start_s - SEGMENTER_DEFAULT["pre_roll_s"] + 1e-9)
        # stream shorter than the pre-roll before the onset: segment starts at the first frame of the stream
        k2, v2 = build(t, lambda x: sign_profile(x, 0.15, 1.6))
        ev2 = [e for _, e in feed(SignSegmenter(CKPT_CFG), t, k2, v2)[0]][0]
        self.assertEqual(ev2.t[0], t[0])

    def test_k_dropped_frames_still_one_emit(self):
        t_full = self.times(3.5)
        k_full, v_full = build(t_full, lambda x: sign_profile(x, 1.0, 2.5))
        _, (a, b) = offline_activity(k_full, v_full, self.fps)
        pattern = [True, False, True, False, False]   # keep 1 drop 1, then keep 1 drop 2 (fixed, repeated)
        keep = np.array([pattern[i % len(pattern)] for i in range(len(t_full))])
        t, k, v = t_full[keep], k_full[keep], v_full[keep]
        events, _ = feed(SignSegmenter(CKPT_CFG), t, k, v)
        self.assertEqual(len(events), 1)
        ev = events[0][1]
        self.assertIsInstance(ev, Emit)
        self.assertLessEqual(ev.t[0], t_full[a])
        self.assertGreaterEqual(ev.t[-1], t_full[b - 1])

    def test_l_reset(self):
        t = self.times(2.0)
        k, v = build(t, lambda x: sign_profile(x, 0.5, 3.0))
        seg = SignSegmenter(CKPT_CFG)
        self.assertIsNone(seg.reset())               # idle -> None
        feed(seg, t, k, v)
        self.assertEqual(seg.state, "recording")
        ev = seg.reset()
        self.assertIsInstance(ev, Discard)
        self.assertEqual(ev.reason, "reset")
        self.assertEqual((seg.state, seg.n_frames), ("idle", 0))
        self.assertIsNone(seg.reset())

    def test_m_buffer_bounded(self):
        t = self.times(60.0, fps=60.0)
        k, v = build(t, lambda x: UP_Y if x >= 0.5 else REST_Y)
        for params, cap in ((None, SEGMENTER_DEFAULT["max_buffer_frames"]), ({"max_buffer_frames": 64}, 64)):
            seg = SignSegmenter(CKPT_CFG, params)
            reasons, max_n = [], 0
            for i, x in enumerate(t):
                ev = seg.push(k[i], v[i], x, SQUARE)
                max_n = max(max_n, seg.n_frames, len(seg._hist))
                if ev is not None:
                    reasons.append(ev.reason)
            with self.subTest(cap=cap):
                self.assertLessEqual(max_n, cap)
                self.assertEqual(reasons, ["too_long"])

    def test_n_constraints(self):
        for params in ({"rest_hold_s": 0.25}, {"rest_hold_s": 0.2}, {"pre_roll_s": 0.05},
                       {"rest_hold_s": 0.05}, {"max_buffer_frames": 1}, {"unknown": 1}, {"max_sign_s": float("nan")}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                SignSegmenter(CKPT_CFG, params)

    def test_o_no_torch_cv2_mediapipe(self):
        code = ("import sys; import src.inference.sign_segmenter; "
                "print(sorted(m for m in ('torch', 'cv2', 'mediapipe') if m in sys.modules))")
        out = subprocess.run([sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True,
                             timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
