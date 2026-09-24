#!/usr/bin/env python3
"""
Real webcam collection for VSL Level 1 (fingerspelling), replacing the synthetic
data/vsl_alphabet_pilot (see its DO_NOT_TRAIN_SYNTHETIC.md).

Every landmark written here comes from MediaPipe Hands running on live camera frames.
Nothing is generated, interpolated or templated.

Output (read directly by vsl_alphabet_cloud_training.ipynb / VSLAlphabetDataset):
  data/vsl_alphabet_real/
    signers.json                      anonymous registry: P001 -> dominant hand, consent flags (no names)
    sessions/<session_id>.json        background, lighting, camera, date, operator notes
    landmarks/<signer>/<sample_id>.npz  raw_landmarks (T,21,3) float32 MediaPipe image coords,
                                      detected_mask (T,), handedness_label (T,), handedness_score (T,),
                                      timestamps_s (T,), handedness (majority label, str)
    metadata/<signer>/<sample_id>.json  per-take metadata incl. QA metrics
    videos/<signer>/<sample_id>.mp4   raw (unmirrored) camera video, for sign verification (gitignored)
    rejected_attempts.jsonl           every take that failed QA, with reasons
    splits/{train,val,test}.csv, classes.txt   written by --make-splits (signer-disjoint)

Take structure (wall-clock, recorded frame indices go into the split CSV):
  countdown (not recorded) -> APPROACH 1.0 s -> HOLD 2.0 s -> RETURN 0.5 s
  hold_start_frame / hold_end_frame = first/last+1 frame index of the HOLD phase.

Usage:
  # 1) register a participant (after written consent is collected on paper)
  python scripts/collect_alphabet_real.py register --dominant-hand Right --consent-confirmed
  # 2) record a session
  python scripts/collect_alphabet_real.py record --signer P001 --reps 10 \
      --background "plain wall" --lighting "indoor daylight" [--camera 0] [--no-video]
  # 3) mark signs verified by a Deaf signer / interpreter (per signer)
  python scripts/collect_alphabet_real.py verify --signer P001 --verified-by "interpreter:NTH"
  # 4) build signer-disjoint splits
  python scripts/collect_alphabet_real.py make-splits --val-signers P004,P007 --test-signers P002,P009

Keys during `record`:  SPACE start take | R redo last take | S skip symbol | Q quit (progress is kept)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = PROJECT_ROOT / "data" / "vsl_alphabet_real"
SYNTHETIC_MARKER = "DO_NOT_TRAIN_SYNTHETIC.md"

# Same 25 labels and order as the notebook/backend (sorted(); Đ sorts last).
CLASSES = ["A", "B", "C", "D", "Dau_moc", "Dau_mu", "E", "G", "H", "I", "K", "L", "M",
           "N", "O", "P", "Q", "R", "S", "T", "U", "V", "X", "Y", "Đ"]
SYMBOL_TYPE = {c: ("accent" if c.startswith("Dau_") else "letter") for c in CLASSES}

# On-screen guidance (docs/alphabet_collection_protocol_v2.md, Thông tư 17/2020/TT-BGDĐT).
# Operator must still have a Deaf signer / interpreter confirm the recorded signs (`verify`).
GUIDE = {
    "A": "Nắm tay, ngón cái áp sát cạnh ngoài ngón trỏ",
    "B": "Bàn tay mở, 4 ngón khép duỗi thẳng, ngón cái gập ngang lòng bàn tay",
    "C": "Bàn tay uốn cong hình chữ C hướng về phía trước",
    "D": "Ngón trỏ chỉ lên, các ngón còn lại chạm đầu ngón cái tạo vòng tròn",
    "Đ": "Như chữ D với nét vạch ngang đặc trưng của VSL",
    "E": "Các ngón tay cong quặp, đầu ngón tì lên ngón cái",
    "G": "Ngón trỏ và ngón cái duỗi song song hướng ngang ra trước",
    "H": "Ngón trỏ và ngón giữa duỗi khép song song hướng ngang, ngón cái gập",
    "I": "Ngón út duỗi thẳng đứng, 3 ngón giữa gập, ngón cái giữ qua",
    "K": "Ngón trỏ hướng lên, ngón giữa hướng ra trước, ngón cái kẹp giữa",
    "L": "Hình chữ L: ngón cái ngang, ngón trỏ thẳng đứng",
    "M": "Nắm tay, 3 ngón (trỏ, giữa, áp út) phủ lên ngón cái",
    "N": "Nắm tay, 2 ngón (trỏ, giữa) phủ lên ngón cái",
    "O": "Các đầu ngón chạm đầu ngón cái tạo hình tròn chữ O",
    "P": "Hình chữ K nhưng chúc đầu ngón xuống dưới",
    "Q": "Hình chữ G nhưng chúc đầu ngón xuống dưới",
    "R": "Ngón trỏ và ngón giữa bắt chéo",
    "S": "Nắm tay, ngón cái vắt ngang qua mu 4 ngón",
    "T": "Nắm tay, ngón cái luồn giữa ngón trỏ và ngón giữa",
    "U": "Ngón trỏ và ngón giữa duỗi khép hướng lên, ngón cái gập",
    "V": "Ngón trỏ và ngón giữa xòe hình chữ V",
    "X": "Ngón trỏ uốn cong hình móc câu, các ngón khác nắm",
    "Y": "Ngón cái và ngón út xòe hai bên, 3 ngón giữa gập",
    "Dau_mu": "Dấu mũ (^): ngón trỏ và ngón giữa tạo hình chữ V ngược",
    "Dau_moc": "Dấu móc/râu: ngón trỏ uốn cong thành hình móc",
}
DISPLAY = {c: c for c in CLASSES} | {"Dau_mu": "Dấu mũ (^)", "Dau_moc": "Dấu móc (ơ, ư)"}

APPROACH_S, HOLD_S, RETURN_S, COUNTDOWN_S = 1.0, 2.0, 0.5, 3
QA = {
    "min_hold_detection_rate": 0.90,  # fraction of HOLD frames with a detected hand
    "max_hold_wrist_drift": 0.05,     # max wrist displacement during HOLD, image-normalized units
    "min_handedness_agreement": 0.80,  # fraction of detected HOLD frames matching the majority hand label
}
SPLIT_COLUMNS = ["sample_id", "signer_id", "symbol", "symbol_type", "handedness", "repetition",
                 "hold_start_frame", "hold_end_frame", "landmark_path", "source_video", "split"]


# ----------------------------------------------------------------------------- helpers
def guard_out_dir(out: Path) -> None:
    if (out / SYNTHETIC_MARKER).exists() or out.name == "vsl_alphabet_pilot":
        sys.exit(f"[REFUSED] {out} is the synthetic pilot directory — real recordings must go elsewhere.")


def load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def rel(path: Path) -> str:
    """Repo-relative POSIX path, as the split CSV / dataset expects (e.g. data/vsl_alphabet_real/...)."""
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sample_id_for(signer: str, symbol: str, rep: int) -> str:
    return f"VSL_ALPHA_REAL_{signer}_{symbol}_REP{rep:02d}"


class TextRenderer:
    """Vietnamese-capable text overlay (cv2.putText cannot draw diacritics)."""

    def __init__(self):
        from PIL import ImageFont
        self.fonts = {}
        for cand in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"):
            if Path(cand).exists():
                self.path = cand
                break
        else:
            self.path = None
        self._ImageFont = ImageFont

    def font(self, size: int):
        if size not in self.fonts:
            self.fonts[size] = (self._ImageFont.truetype(self.path, size) if self.path
                                else self._ImageFont.load_default())
        return self.fonts[size]

    def draw(self, frame_bgr, lines: list[tuple[str, int, tuple[int, int, int]]], origin=(20, 20)):
        from PIL import Image, ImageDraw
        img = Image.fromarray(frame_bgr[:, :, ::-1])
        d = ImageDraw.Draw(img)
        x, y = origin
        for text, size, rgb in lines:
            f = self.font(size)
            d.text((x + 2, y + 2), text, font=f, fill=(0, 0, 0))
            d.text((x, y), text, font=f, fill=rgb)
            y += int(size * 1.35)
        return np.asarray(img)[:, :, ::-1].copy()


# ----------------------------------------------------------------------------- register / verify
def cmd_register(args) -> None:
    out = Path(args.out); guard_out_dir(out)
    if not args.consent_confirmed:
        sys.exit("[REFUSED] Collect signed consent first, then pass --consent-confirmed.")
    reg_path = out / "signers.json"
    reg = load_json(reg_path, {})
    sid = f"P{len(reg) + 1:03d}"
    reg[sid] = {
        "dominant_hand": args.dominant_hand,
        "consent_confirmed": True,
        "consent_date": dt.date.today().isoformat(),
        "is_deaf_or_fluent_signer": args.fluent_signer,
        "signs_verified_by": None,
        "notes": args.notes or "",
    }
    save_json(reg_path, reg)
    print(f"Registered anonymous signer {sid} (store the name<->ID mapping OFF this repo, on paper).")


def cmd_verify(args) -> None:
    out = Path(args.out); guard_out_dir(out)
    reg_path = out / "signers.json"
    reg = load_json(reg_path, {})
    if args.signer not in reg:
        sys.exit(f"Unknown signer {args.signer}")
    reg[args.signer]["signs_verified_by"] = args.verified_by
    reg[args.signer]["signs_verified_date"] = dt.date.today().isoformat()
    save_json(reg_path, reg)
    print(f"{args.signer}: signs marked verified by {args.verified_by}")


# ----------------------------------------------------------------------------- recording
def qa_take(raw, detected, labels, hold_start, hold_end) -> tuple[dict, list[str]]:
    hold = slice(hold_start, hold_end)
    det = detected[hold]
    rate = float(det.mean()) if det.size else 0.0
    wrist = raw[hold][det][:, 0, :2]
    drift = float(np.max(np.linalg.norm(wrist - wrist[0], axis=-1))) if len(wrist) else float("inf")
    hold_labels = [l for l, d in zip(labels[hold], det) if d]
    majority, agree = (Counter(hold_labels).most_common(1)[0] if hold_labels else ("", 0))
    agreement = agree / len(hold_labels) if hold_labels else 0.0
    m = {"hold_detection_rate": rate, "hold_wrist_drift_max": drift,
         "handedness_majority": majority, "handedness_agreement": agreement,
         "n_frames": int(len(detected)), "hold_frames": int(hold_end - hold_start)}
    reasons = []
    if rate < QA["min_hold_detection_rate"]:
        reasons.append(f"hold detection {rate:.0%} < {QA['min_hold_detection_rate']:.0%}")
    if drift > QA["max_hold_wrist_drift"]:
        reasons.append(f"wrist drift {drift:.3f} > {QA['max_hold_wrist_drift']}")
    if agreement < QA["min_handedness_agreement"]:
        reasons.append(f"handedness agreement {agreement:.0%} < {QA['min_handedness_agreement']:.0%}")
    return m, reasons


def record_take(cap, hands, text, symbol, header):
    """Countdown, then capture APPROACH/HOLD/RETURN. Returns arrays + frames, or None if user aborted."""
    import cv2
    t0 = time.time()
    while time.time() - t0 < COUNTDOWN_S:  # countdown — not recorded
        ok, frame = cap.read()
        if not ok:
            return None
        left = COUNTDOWN_S - int(time.time() - t0)
        view = text.draw(cv2.flip(frame, 1), [(header, 26, (255, 255, 255)),
                                              (f"Chuẩn bị: {DISPLAY[symbol]}", 40, (255, 220, 0)),
                                              (GUIDE[symbol], 24, (255, 255, 255)),
                                              (f"Bắt đầu sau {left}...", 48, (255, 80, 80))])
        cv2.imshow("VSL collect", view)
        if (cv2.waitKey(1) & 0xFF) == ord("q"):
            return None

    raw, det, lab, score, ts, frames = [], [], [], [], [], []
    hold_start = hold_end = None
    t0 = time.time()
    total = APPROACH_S + HOLD_S + RETURN_S
    while True:
        ok, frame = cap.read()
        if not ok:
            return None
        t = time.time() - t0
        if t >= total:
            break
        idx = len(raw)
        if hold_start is None and t >= APPROACH_S:
            hold_start = idx
        if hold_end is None and t >= APPROACH_S + HOLD_S:
            hold_end = idx
        res = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))  # raw, unmirrored frame (same as backend)
        if res.multi_hand_landmarks:
            lm = res.multi_hand_landmarks[0].landmark
            raw.append(np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float32))
            c = res.multi_handedness[0].classification[0]
            det.append(True); lab.append(c.label); score.append(float(c.score))
        else:
            raw.append(np.zeros((21, 3), dtype=np.float32))
            det.append(False); lab.append(""); score.append(0.0)
        ts.append(t)
        frames.append(frame)

        phase = "TIẾN TAY" if t < APPROACH_S else ("GIỮ YÊN" if t < APPROACH_S + HOLD_S else "HẠ TAY")
        colour = (80, 255, 80) if phase == "GIỮ YÊN" else (255, 220, 0)
        view = text.draw(cv2.flip(frame, 1), [(header, 26, (255, 255, 255)),
                                              (f"{DISPLAY[symbol]} — {phase}", 44, colour),
                                              ("● REC" + ("  (không thấy tay)" if not det[-1] else ""), 26, (255, 60, 60))])
        cv2.imshow("VSL collect", view)
        cv2.waitKey(1)
    if hold_start is None or hold_end is None or hold_end <= hold_start:
        return None
    return (np.stack(raw), np.array(det, dtype=bool), np.array(lab), np.array(score, dtype=np.float32),
            np.array(ts, dtype=np.float32), frames, hold_start, hold_end)


def save_take(out, signer, symbol, rep, session_id, take, qa_metrics, save_video, reg_entry, session):
    import cv2
    raw, det, lab, score, ts, frames, hs, he = take
    sid = sample_id_for(signer, symbol, rep)
    npz = out / "landmarks" / signer / f"{sid}.npz"
    npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(npz, raw_landmarks=raw, detected_mask=det, handedness_label=lab,
                        handedness_score=score, timestamps_s=ts, handedness=qa_metrics["handedness_majority"])
    video = out / "videos" / signer / f"{sid}.mp4"
    if save_video:
        video.parent.mkdir(parents=True, exist_ok=True)
        fps = (len(ts) - 1) / max(ts[-1] - ts[0], 1e-6)
        h, w = frames[0].shape[:2]
        wr = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        for f in frames:
            wr.write(f)
        wr.release()
    meta = {
        "sample_id": sid, "signer_id": signer, "symbol": symbol, "symbol_type": SYMBOL_TYPE[symbol],
        "repetition": rep, "session_id": session_id,
        "handedness": qa_metrics["handedness_majority"], "dominant_hand_declared": reg_entry["dominant_hand"],
        "hold_start_frame": hs, "hold_end_frame": he,
        "landmark_path": rel(npz), "source_video": rel(video) if save_video else "",
        "fps_effective": round((len(ts) - 1) / max(float(ts[-1] - ts[0]), 1e-6), 2),
        "background": session["background"], "lighting": session["lighting"], "recorded_at": session["date"],
        "qa": qa_metrics,
        "provenance": "live webcam -> MediaPipe Hands (scripts/collect_alphabet_real.py); no synthetic data",
    }
    save_json(out / "metadata" / signer / f"{sid}.json", meta)
    return meta


def cmd_record(args) -> None:
    import cv2
    import mediapipe as mp

    out = Path(args.out); guard_out_dir(out)
    reg = load_json(out / "signers.json", {})
    if args.signer not in reg:
        sys.exit(f"Unknown signer {args.signer}. Run `register` first (consent required).")
    if not reg[args.signer].get("consent_confirmed"):
        sys.exit(f"{args.signer} has no confirmed consent.")

    session_id = f"{args.signer}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        sys.exit(f"Cannot open camera {args.camera}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, 30)
    session = {
        "session_id": session_id, "signer_id": args.signer, "date": dt.datetime.now().isoformat(timespec="seconds"),
        "background": args.background, "lighting": args.lighting, "camera_index": args.camera,
        "actual_resolution": [int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))],
        "reported_fps": float(cap.get(cv2.CAP_PROP_FPS)), "reps": args.reps, "notes": args.notes or "",
        "mediapipe_version": mp.__version__, "qa_thresholds": QA,
        "phases_s": {"approach": APPROACH_S, "hold": HOLD_S, "return": RETURN_S},
    }
    save_json(out / "sessions" / f"{session_id}.json", session)

    # Plan: every rep covers all symbols, symbol order shuffled per rep (avoids order effects).
    rng = random.Random(f"{args.signer}-{session_id}")
    plan = []
    for rep in range(1, args.reps + 1):
        order = CLASSES[:]; rng.shuffle(order)
        plan += [(s, rep) for s in order]
    plan = [(s, r) for s, r in plan
            if not (out / "landmarks" / args.signer / f"{sample_id_for(args.signer, s, r)}.npz").exists()]
    print(f"{len(plan)} takes to record for {args.signer} (existing takes are skipped).")

    text = TextRenderer()
    hands = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=1, model_complexity=1,
                                     min_detection_confidence=0.5, min_tracking_confidence=0.5)
    done, i, last_saved = 0, 0, None
    try:
        while i < len(plan):
            symbol, rep = plan[i]
            header = f"{args.signer} | lượt {rep}/{args.reps} | {i + 1}/{len(plan)} | SPACE: quay  R: quay lại  S: bỏ qua  Q: thoát"
            ok, frame = cap.read()
            if not ok:
                break
            view = text.draw(cv2.flip(frame, 1), [(header, 22, (255, 255, 255)),
                                                  (f"Ký hiệu: {DISPLAY[symbol]}", 48, (255, 220, 0)),
                                                  (GUIDE[symbol], 24, (255, 255, 255)),
                                                  ("Nhấn SPACE khi sẵn sàng", 28, (160, 255, 160))])
            cv2.imshow("VSL collect", view)
            key = cv2.waitKey(20) & 0xFF
            if key == ord("q"):
                break
            if key == ord("s"):
                i += 1
                last_saved = None
                continue
            if key == ord("r") and last_saved is not None:
                for p in last_saved:
                    Path(p).unlink(missing_ok=True)
                i = max(0, i - 1)
                last_saved = None
                continue
            if key != ord(" "):
                continue

            take = record_take(cap, hands, text, symbol, header)
            if take is None:
                continue
            metrics, reasons = qa_take(take[0], take[1], take[2], take[6], take[7])
            if reasons:
                with open(out / "rejected_attempts.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"signer_id": args.signer, "symbol": symbol, "repetition": rep,
                                        "session_id": session_id, "reasons": reasons, "qa": metrics,
                                        "time": dt.datetime.now().isoformat(timespec="seconds")},
                                       ensure_ascii=False) + "\n")
                print(f"  RETAKE {symbol} rep {rep}: {'; '.join(reasons)}")
                continue  # same (symbol, rep) again
            meta = save_take(out, args.signer, symbol, rep, session_id, take, metrics,
                             not args.no_video, reg[args.signer], session)
            last_saved = [PROJECT_ROOT / meta["landmark_path"],
                          out / "metadata" / args.signer / f"{meta['sample_id']}.json"] + \
                         ([PROJECT_ROOT / meta["source_video"]] if meta["source_video"] else [])
            done += 1
            i += 1
            print(f"  saved {meta['sample_id']} (hold det {metrics['hold_detection_rate']:.0%}, "
                  f"drift {metrics['hold_wrist_drift_max']:.3f}, hand {metrics['handedness_majority']})")
    finally:
        hands.close(); cap.release(); cv2.destroyAllWindows()
    print(f"Session {session_id}: {done} takes saved.")


# ----------------------------------------------------------------------------- splits
def cmd_make_splits(args) -> None:
    out = Path(args.out); guard_out_dir(out)
    reg = load_json(out / "signers.json", {})
    rows = []
    for mp_ in sorted((out / "metadata").glob("*/*.json")):
        m = json.loads(mp_.read_text(encoding="utf-8"))
        if not (PROJECT_ROOT / m["landmark_path"]).exists():
            print(f"  skip {m['sample_id']}: landmark file missing"); continue
        rows.append(m)
    signers = sorted({r["signer_id"] for r in rows})
    val = [s for s in (args.val_signers or "").split(",") if s]
    test = [s for s in (args.test_signers or "").split(",") if s]
    if not val or not test:
        sys.exit(f"Pass --val-signers and --test-signers explicitly. Signers with data: {signers}")
    train = [s for s in signers if s not in val + test]
    if set(val) & set(test) or not train:
        sys.exit("val/test must be disjoint and leave at least one train signer")
    if missing := [s for s in val + test if s not in signers]:
        sys.exit(f"No data for signers {missing}")
    unverified = [s for s in signers if not reg.get(s, {}).get("signs_verified_by")]
    if unverified and not args.allow_unverified:
        sys.exit(f"Signs not yet verified by a Deaf signer/interpreter for {unverified} "
                 f"(run `verify`, or pass --allow-unverified for a pilot run and say so in the report)")

    split_of = {s: "train" for s in train} | {s: "val" for s in val} | {s: "test" for s in test}
    sdir = out / "splits"; sdir.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        part = [r for r in rows if split_of[r["signer_id"]] == split]
        with open(sdir / f"{split}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=SPLIT_COLUMNS)
            w.writeheader()
            for r in sorted(part, key=lambda r: r["sample_id"]):
                w.writerow({k: (split if k == "split" else r.get(k, "")) for k in SPLIT_COLUMNS})
        per_class = Counter(r["symbol"] for r in part)
        thin = [c for c in CLASSES if per_class[c] == 0]
        print(f"{split}: {len(part)} samples, signers={sorted({r['signer_id'] for r in part})}"
              + (f"  WARNING classes with 0 samples: {thin}" if thin else ""))
    (sdir / "classes.txt").write_text("\n".join(CLASSES) + "\n", encoding="utf-8")
    save_json(sdir / "split_info.json", {"train": train, "val": val, "test": test, "created": dt.datetime.now().isoformat(timespec="seconds"),
                                         "unverified_signers": unverified})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("register"); p.set_defaults(fn=cmd_register)
    p.add_argument("--dominant-hand", choices=["Right", "Left"], required=True)
    p.add_argument("--consent-confirmed", action="store_true")
    p.add_argument("--fluent-signer", action="store_true", help="participant is Deaf or a fluent VSL signer")
    p.add_argument("--notes")

    p = sub.add_parser("record"); p.set_defaults(fn=cmd_record)
    p.add_argument("--signer", required=True)
    p.add_argument("--reps", type=int, default=10)
    p.add_argument("--background", required=True, help='e.g. "plain wall", "bookshelf", "outdoor"')
    p.add_argument("--lighting", required=True, help='e.g. "indoor daylight", "warm lamp", "backlit"')
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--no-video", action="store_true", help="store landmarks only (no face video)")
    p.add_argument("--notes")

    p = sub.add_parser("verify"); p.set_defaults(fn=cmd_verify)
    p.add_argument("--signer", required=True)
    p.add_argument("--verified-by", required=True, help='role + initials, e.g. "interpreter:NTH"')

    p = sub.add_parser("make-splits"); p.set_defaults(fn=cmd_make_splits)
    p.add_argument("--val-signers")
    p.add_argument("--test-signers")
    p.add_argument("--allow-unverified", action="store_true")

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
