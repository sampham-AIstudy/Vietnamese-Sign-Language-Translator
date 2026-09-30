"""
Plan 06 §3.7 / AC12: end-to-end run of the full stack on a real clip.

    PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/e2e_fullstack.py --scenario fingerspell|word \
        [--model-type stgcn_h360] --video <mp4> --out reports/e2e_<YYYY-MM-DD>/<name>.json

1. starts `powershell -NoProfile -ExecutionPolicy Bypass -File start_fullstack.ps1` (the Bypass applies to this
   process only; the machine policy is not changed), with VSL_MODEL_TYPE set only when --model-type is given
   (the default model is never changed; VSL_MODEL_TYPE / VSL_CORS_ORIGINS of the caller are removed otherwise);
2. waits for GET http://127.0.0.1:8000/api/health == 200 and http://localhost:3000/ == 200 (180 s in total);
3. writes a Y4M of the clip OUTSIDE the repository (scripts/make_fake_webcam_y4m.py) and runs
   `node scripts/e2e_browser.cjs` (Edge + fake webcam fed by that Y4M);
4. stops the process tree (`taskkill /T /F /PID`), checks that no child process is left and that ports 8000 and
   3000 are free;
5. writes the JSON: generated_by{command, git_commit, code_dirty}, versions (node / Edge / mediapipe), the clip id
   (no absolute path, no landmark, no image), the observations of the browser, and one entry per AC12 check.
   Plan 06 revision 4 (0D.3): the check `tab_unmounted_owner_rule` reads the source module of every
   `new WebSocket(...)` of the page (observations.ws_page, recorded by the page hook of e2e_browser.cjs, 0D.5): in the
   fingerspell scenario every socket of the tab_unmounted path must have exactly one record whose first app frame is
   /src/components/Phase12Pipeline.jsx (SCENARIO_TAB_UNMOUNTED_OWNER); missing page data is red in every scenario.
   `ws_classification.page_hook` (records / CDP sockets by path, owners, click phase) is information, not a check.
The prediction of the clip is written under `info_not_accuracy`: one TRAIN clip per scenario only shows that the
stack runs; it is not an accuracy figure. TEST / VAL clips are refused.
Exit code 0 only when every check passes.
"""
import argparse
import csv
import datetime as dt
import importlib.metadata
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

import psutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_fake_webcam_y4m  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HEALTH_URL = "http://127.0.0.1:8000/api/health"
PAGE_URL = "http://localhost:3000/"
PORTS = (8000, 3000)
WS_PREFIX = "ws://localhost:3000/ws/"
READY_TIMEOUT_S = 180.0
MAX_SEQUENCE_FRAMES = 300
MAX_ABS_VALUE = 10.0
UNIFIED_SPLITS = os.path.join(ROOT, "data", "splits", "unified")
HAUUTO_MANIFEST = os.path.join(ROOT, "data", "external", "alphabet_hands_kaggle", "alphabet_hands", "manifest.csv")
CODE_PATHS = ("backend", "src", "frontend", "scripts", "tests")
NOTE = ("End-to-end run on ONE training clip per scenario: shows that backend + frontend run together through the "
        "Vite proxy with a fake webcam fed by a real clip. Not an accuracy measurement; the prediction is recorded "
        "under info_not_accuracy only. The fake webcam replays the clip converted to Y4M (cv2 BGR->I420), so the "
        "frames are not bit-identical to the mp4 decoded by cv2.")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def _rel(path: str) -> str:
    return os.path.relpath(os.path.abspath(path), ROOT).replace("\\", "/")


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _ports_listening() -> dict:
    return {str(p): _port_open(p) for p in PORTS}


def _http_get(url: str, timeout: float = 5.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except (urllib.error.URLError, OSError, TimeoutError):
        return None, None


# ----------------------------------------------------------------------------------------------------------------
def clip_identity(video: str) -> dict:
    """Clip id / label from the split files; a clip of the unified VAL or TEST split is refused."""
    name = os.path.basename(video)
    stem = os.path.splitext(name)[0]
    for split in ("val", "test"):
        p = os.path.join(UNIFIED_SPLITS, f"{split}.csv")
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["file_name"] == name:
                    raise SystemExit(f"refused: {name} belongs to the unified {split.upper()} split")
    with open(os.path.join(UNIFIED_SPLITS, "train.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["file_name"] == name:
                return {"clip_id": r["video_id"], "source": r["source"], "split": "train",
                        "label": r["gloss_normalized"], "label_kind": "gloss (data/splits/unified/train.csv)"}
    sample_id = f"hauuto_{stem}"
    with open(HAUUTO_MANIFEST, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["sample_id"] == sample_id:
                return {"clip_id": sample_id, "source": "hauuto", "split": "Level 1 training data (hauuto)",
                        "label": r["symbol"], "label_kind": "symbol (alphabet_hands manifest.csv)"}
    raise SystemExit(f"refused: {name} is neither a unified TRAIN clip nor a hauuto clip of the manifest")


def video_facts(video: str) -> dict:
    import cv2
    cap = cv2.VideoCapture(video)
    try:
        return {"frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), "fps": float(cap.get(cv2.CAP_PROP_FPS)),
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}
    finally:
        cap.release()


# ----------------------------------------------------------------------------------------------------------------
def start_stack(env: dict, log_path: str) -> subprocess.Popen:
    logf = open(log_path, "wb")
    return subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "start_fullstack.ps1"],
        cwd=ROOT, env=env, stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))


def wait_ready(t_start: float) -> dict:
    out = {"health_status": None, "health": None, "health_wait_s": None, "page_status": None, "page_wait_s": None}
    while time.monotonic() - t_start < READY_TIMEOUT_S:
        code, body = _http_get(HEALTH_URL)
        if code is not None and out["health_status"] != 200:
            out["health_status"] = code
        if code == 200:
            out["health_wait_s"] = round(time.monotonic() - t_start, 1)
            h = json.loads(body)
            out["health"] = {k: h.get(k) for k in ("status", "model_type", "is_default_model", "pipeline",
                                                  "checkpoint", "num_classes", "device")}
            break
        time.sleep(1.0)
    while out["health_status"] == 200 and time.monotonic() - t_start < READY_TIMEOUT_S:
        code, _ = _http_get(PAGE_URL)
        out["page_status"] = code
        if code == 200:
            out["page_wait_s"] = round(time.monotonic() - t_start, 1)
            break
        time.sleep(1.0)
    return out


def stop_stack(proc: subprocess.Popen) -> dict:
    try:
        tree = [proc.pid] + [c.pid for c in psutil.Process(proc.pid).children(recursive=True)]
    except psutil.NoSuchProcess:
        tree = [proc.pid]
    snapshot = {}
    for pid in tree:
        try:
            p = psutil.Process(pid)
            snapshot[pid] = (p.create_time(), p.name())
        except psutil.NoSuchProcess:
            pass
    tk = subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, text=True)
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        pass
    deadline = time.monotonic() + 20
    alive = []
    while time.monotonic() < deadline:
        alive = []
        for pid, (ctime, name) in snapshot.items():
            try:
                p = psutil.Process(pid)
                if p.create_time() == ctime and p.status() != psutil.STATUS_ZOMBIE:
                    alive.append(name)
            except psutil.NoSuchProcess:
                pass
        ports = _ports_listening()
        if not alive and not any(ports.values()):
            break
        time.sleep(0.5)
    return {"taskkill_exit": tk.returncode, "process_tree_names": sorted(n for _, n in snapshot.values()),
            "processes_alive_after_stop": sorted(alive), "ports_listening_after_stop": _ports_listening()}


# ----------------------------------------------------------------------------------------------------------------
def check(checks: dict, name: str, ok: bool, detail=None) -> None:
    checks[name] = {"pass": bool(ok), "detail": detail}


# Plan 06 revision 2, 0B.1: the Vite dev client (/@vite/client, injected by `npm run dev`; not in frontend/src, not
# in the build) opens its own HMR socket on the page origin. A socket is that HMR socket ONLY when all three hold:
# (1) the URL matches the whole regex below, (2) the handshake Sec-WebSocket-Protocol is exactly "vite-hmr",
# (3) every message received is JSON with type == "connected". It is excluded from the "via /ws/" check only;
# the ":8000" ban applies to every socket without exception.
VITE_HMR_URL_RE = re.compile(r"^ws://localhost:3000/\?token=[A-Za-z0-9_-]+$")
VITE_HMR_PROTOCOL = "vite-hmr"
VITE_HMR_MESSAGE_TYPES = frozenset({"connected"})
MAX_HMR_SOCKETS = 1


def _ws_brief(w: dict) -> dict:
    return {"url": w.get("url"), "protocol": w.get("protocol"), "count_by_type": dict(w.get("count_by_type") or {})}


def _hmr_rule_failures(w: dict) -> list:
    """Which of the conditions (1)-(3) of 0B.1 a socket fails (empty list = Vite HMR socket)."""
    fails = []
    # fullmatch: the WHOLE URL must match (a trailing newline, which "$" alone would let through, is refused)
    url = w.get("url") or ""
    if not VITE_HMR_URL_RE.fullmatch(url):
        fails.append("url")
    if w.get("protocol") != VITE_HMR_PROTOCOL:
        fails.append("protocol")
    cbt = w.get("count_by_type") or {}
    # every message must be JSON with type "connected": no other type, and no message outside count_by_type
    # (non-JSON messages are counted in n_messages only)
    if set(cbt) - VITE_HMR_MESSAGE_TYPES or w.get("n_messages", 0) != sum(cbt.values()):
        fails.append("message_types")
    return fails


def classify_ws(ws_list: list) -> dict:
    """Pure: split the observed sockets into the Vite HMR socket(s) and the app sockets, and evaluate the three
    URL checks of AC12 (revision 2): ws_no_8000_any_socket, ws_app_urls_via_proxy, vite_hmr_socket_rule."""
    hmr, app, protocol_violations = [], [], []
    for w in ws_list:
        fails = _hmr_rule_failures(w)
        if not fails:
            hmr.append(w)
        else:
            app.append(w)
            if w.get("protocol") == VITE_HMR_PROTOCOL:
                protocol_violations.append({**_ws_brief(w), "fails": fails})
    checks: dict = {}
    with_8000 = [_ws_brief(w) for w in ws_list if ":8000" in (w.get("url") or "")]
    check(checks, "ws_no_8000_any_socket", not with_8000,
          {"n_sockets": len(ws_list), "violations": with_8000})
    outside = [_ws_brief(w) for w in app if not (w.get("url") or "").startswith(WS_PREFIX)]
    check(checks, "ws_app_urls_via_proxy", len(app) >= 1 and not outside,
          {"app_urls": [w.get("url") for w in app], "violations": outside})
    check(checks, "vite_hmr_socket_rule", len(hmr) <= MAX_HMR_SOCKETS and not protocol_violations,
          {"n_hmr": len(hmr), "max_hmr": MAX_HMR_SOCKETS, "hmr_excluded": [_ws_brief(w) for w in hmr],
           "vite_hmr_protocol_but_not_hmr": protocol_violations})
    return {"hmr": hmr, "app": app, "hmr_excluded": [_ws_brief(w) for w in hmr], "checks": checks}


def strictmode_orphans(sockets_of_path: list) -> dict:
    """Pure (0B.2): React.StrictMode mounts, unmounts and mounts again in dev, so a component opens a socket, closes
    it and opens another. On ONE path (sockets in creation order) a socket is a StrictMode orphan -- exempt from the
    "first message is session_info" check -- only when it received 0 messages, is closed, and is not the last
    socket of the path; at most one orphan per path. Every other socket is `checked` (its first message must be
    session_info; the caller checks that). The last socket must have received messages."""
    n = len(sockets_of_path)
    orphans, checked, violations = [], [], []
    if n == 0:
        violations.append("no socket on this path")
    for i, w in enumerate(sockets_of_path):
        last = i == n - 1
        if w.get("n_messages", 0) == 0:
            if last:
                violations.append(f"socket {i}: 0 messages and it is the last socket of the path")
            elif not w.get("closed"):
                violations.append(f"socket {i}: 0 messages but not closed")
            else:
                orphans.append(i)
                continue
        checked.append(w)
    if len(orphans) > 1:
        violations.append(f"{len(orphans)} orphans on one path (at most 1)")
    return {"n_sockets": n, "orphans": orphans, "checked": checked, "violations": violations,
            "pass": not violations}


def app_ws_by_path(ws_list: list) -> dict:
    """App sockets (every socket that is not the Vite HMR socket of 0B.1) grouped by URL path, creation order."""
    by_path: dict = {}
    for w in classify_ws(ws_list)["app"]:
        by_path.setdefault(urllib.parse.urlparse(w["url"]).path, []).append(w)
    return by_path


# Plan 06 revision 3, 0C.2: every app path has ONE role, fixed by the scenario (a constant, never inferred from the
# observations). `used`: the path the scenario works with -- StrictMode orphan rule of 0B.2, unchanged. `tab_unmounted`:
# the path of the default tab ("Ký từ", App.jsx) that the fingerspell scenario leaves by clicking the "Bảng Chữ Cái"
# tab -- tab_unmounted_socket_rule. Any other app path is red.
SCENARIO_WS_ROLES = {
    "fingerspell": {"used": "/ws/hand-landmarks", "tab_unmounted": "/ws/live-stream",
                    "tab_step": "tab_alphabet", "first_action_step": "record_clicked"},
    "word": {"used": "/ws/live-stream", "tab_unmounted": None, "tab_step": None, "first_action_step": None},
}
MAX_TAB_UNMOUNTED_SOCKETS = 2  # one StrictMode pair: mount -> unmount -> mount
TAB_UNMOUNTED_HANDSHAKE = (None, 101)
TAB_UNMOUNTED_PROTOCOL_VERSION = 2


def _single_step(steps: list, name: str):
    """The step called `name` when there is exactly one (else None)."""
    found = [s for s in (steps or []) if s.get("name") == name]
    return found[0] if len(found) == 1 else None


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def tab_unmounted_violations(sockets: list, steps: list, tab_step: str, first_action_step: str) -> list:
    """Pure (0C.2 item 2, revision 4 of 0D.3): sockets of the path of the default tab unmounted by the tab click.
    0 sockets is allowed; when there are sockets, ALL must hold: (a) <= 2 sockets; the tab step exists exactly once
    with clicked: true and a numeric click_t_s, and each socket has a numeric created_t_s (created_t_s is NOT compared
    with click_t_s any more -- the source of the socket is checked by tab_unmounted_owner_check); (c) each closed in
    the run, closed_t_s not null and <= t_s of the first action step (which must exist); (d) n_non_json == 0 and
    count_by_type empty, or exactly {session_info: 1} with first_type session_info and protocol_version 2;
    (e) handshake_status in {null, 101}."""
    if not sockets:
        return []
    v = []
    if len(sockets) > MAX_TAB_UNMOUNTED_SOCKETS:
        v.append(f"{len(sockets)} sockets (at most {MAX_TAB_UNMOUNTED_SOCKETS})")
    tab = _single_step(steps, tab_step)
    click_t = tab.get("click_t_s") if tab else None
    if tab is None:
        v.append(f"step {tab_step} missing (or not exactly one)")
    elif tab.get("clicked") is not True:
        v.append(f"step {tab_step}: clicked is not true")
    elif not _num(click_t):
        v.append(f"step {tab_step}: click_t_s missing")
    act = _single_step(steps, first_action_step)
    act_t = act.get("t_s") if act else None
    if act is None or not _num(act_t):
        v.append(f"step {first_action_step} missing (or not exactly one)")
    for i, w in enumerate(sockets):
        c = w.get("created_t_s")
        if not _num(c):
            v.append(f"socket {i}: created_t_s missing")
        if w.get("closed") is not True:
            v.append(f"socket {i}: not closed")
        ct = w.get("closed_t_s")
        if not _num(ct):
            v.append(f"socket {i}: closed_t_s is null")
        elif _num(act_t) and not ct <= act_t:
            v.append(f"socket {i}: closed_t_s {ct} after {first_action_step} t_s {act_t}")
        cbt = dict(w.get("count_by_type") or {})
        if w.get("n_non_json") != 0:
            v.append(f"socket {i}: n_non_json = {w.get('n_non_json')}")
        if w.get("n_messages", 0) != sum(cbt.values()) + (w.get("n_non_json") or 0):
            v.append(f"socket {i}: n_messages does not match count_by_type")
        if cbt:
            si = w.get("session_info") or {}
            if cbt != {"session_info": 1}:
                v.append(f"socket {i}: messages {cbt} (only none or one session_info allowed)")
            elif w.get("first_type") != "session_info":
                v.append(f"socket {i}: first_type {w.get('first_type')!r}")
            elif si.get("protocol_version") != TAB_UNMOUNTED_PROTOCOL_VERSION:
                v.append(f"socket {i}: session_info.protocol_version {si.get('protocol_version')!r}")
        if w.get("handshake_status") not in TAB_UNMOUNTED_HANDSHAKE:
            v.append(f"socket {i}: handshake_status {w.get('handshake_status')!r}")
    return v


def scenario_ws_roles(ws_by_path: dict, scenario: str, steps: list) -> dict:
    """Pure (0C.2): role of each app path from the constant table of the scenario, strictmode_orphan_rule on the
    `used` path only (0B.2 rule unchanged; the `used` path without any socket is red) and tab_unmounted_socket_rule
    on every other path (the `tab_unmounted` path of the scenario must satisfy tab_unmounted_violations; any other
    path is red)."""
    if scenario not in SCENARIO_WS_ROLES:
        raise ValueError(f"unknown scenario {scenario!r}")
    table = SCENARIO_WS_ROLES[scenario]
    used, tabp = table["used"], table["tab_unmounted"]
    role_by_path = {used: "used"}
    if tabp:
        role_by_path[tabp] = "tab_unmounted"
    for p in ws_by_path:
        role_by_path.setdefault(p, "other")
    so = strictmode_orphans(ws_by_path.get(used, []))
    checks: dict = {}
    check(checks, "strictmode_orphan_rule", so["pass"],
          {used: {"n_sockets": so["n_sockets"], "orphans": so["orphans"], "violations": so["violations"]}})
    tab_detail, ok = {}, True
    for p, role in role_by_path.items():
        if role == "used":
            continue
        socks = ws_by_path.get(p, [])
        if role == "tab_unmounted":
            viol = tab_unmounted_violations(socks, steps, table["tab_step"], table["first_action_step"])
        else:
            viol = [f"app path {p!r} has no role in scenario {scenario!r} ({len(socks)} sockets)"]
        ok = ok and not viol
        tab_detail[p] = {"role": role, "n_sockets": len(socks), "violations": viol,
                         "sockets": [{k: w.get(k) for k in ("created_t_s", "closed_t_s", "closed", "handshake_status",
                                                            "n_messages", "count_by_type")} for w in socks]}
    check(checks, "tab_unmounted_socket_rule", ok, tab_detail)
    return {"role_by_path": role_by_path,
            "tab_unmounted_by_path": {p: len(ws_by_path.get(p, [])) for p, r in role_by_path.items()
                                      if r == "tab_unmounted"},
            "strictmode_used": so, "checks": checks}


# Plan 06 revision 4, 0D.3: source (owner) of the sockets of the tab_unmounted path = the app module that called
# `new WebSocket(...)`, read from the call stack in the page (page hook of e2e_browser.cjs, 0D.5). A constant fixed
# from the code, never inferred from the observations: App.jsx:9 default tab 'realtime'; App.jsx:53 'realtime' ->
# <Phase12Pipeline />; Phase12Pipeline.jsx:86 is the only `new WebSocket` of that component.
SCENARIO_TAB_UNMOUNTED_OWNER = {"fingerspell": "/src/components/Phase12Pipeline.jsx", "word": None}
APP_SOURCE_PREFIX = "/src/"


def ws_owner(frames):
    """Pure (0D.3): the first frame (innermost first) that starts with /src/, without any `?...` part; None when
    there is none or when `frames` is not a list."""
    if not isinstance(frames, list):
        return None
    for f in frames:
        if isinstance(f, str) and f.startswith(APP_SOURCE_PREFIX):
            return f.split("?", 1)[0]
    return None


def _url_path(url) -> str:
    """URL path, split the way app_ws_by_path does."""
    return urllib.parse.urlparse(str(url or "")).path


def tab_unmounted_owner_check(ws_by_path: dict, page_ws, scenario: str) -> dict:
    """Pure (0D.3): tab_unmounted_owner_rule. (1) unknown scenario -> ValueError; (2) page_ws not a list -> red in
    every scenario (no source data = nothing proven); (3) scenario without a tab_unmounted path -> green, applies
    false; (4) fingerspell: the records of page_ws on the tab_unmounted path P must be exactly as many as the CDP
    sockets of P, and each must have ws_owner(frames) == SCENARIO_TAB_UNMOUNTED_OWNER[scenario]."""
    if scenario not in SCENARIO_TAB_UNMOUNTED_OWNER:
        raise ValueError(f"unknown scenario {scenario!r}")
    p = SCENARIO_WS_ROLES[scenario]["tab_unmounted"]
    if not isinstance(page_ws, list):
        return {"pass": False, "detail": {"applies": p is not None, "violations": ["page hook data missing"]}}
    if p is None:
        return {"pass": True, "detail": {"applies": False, "n_records": len(page_ws), "violations": []}}
    want = SCENARIO_TAB_UNMOUNTED_OWNER[scenario]
    violations = [f"page record {i}: not an object" for i, r in enumerate(page_ws) if not isinstance(r, dict)]
    recs = [r for r in page_ws if isinstance(r, dict) and _url_path(r.get("url")) == p]
    n_cdp = len(ws_by_path.get(p, []))
    if len(recs) != n_cdp:
        violations.append(f"{len(recs)} page records for {n_cdp} CDP sockets on {p}")
    owners = [ws_owner(r.get("frames")) for r in recs]
    for i, (r, o) in enumerate(zip(recs, owners)):
        if o != want:
            violations.append(f"record {i} on {p}: owner {o!r} (expected {want!r})"
                              + (f"; hook_error {r.get('hook_error')!r}" if r.get("hook_error") else ""))
    return {"pass": not violations, "detail": {"applies": True, "path": p, "expected_owner": want,
                                               "n_cdp_sockets": n_cdp, "n_records": len(recs), "owners": owners,
                                               "violations": violations}}


def click_phase(t_page_ms, before_ms, after_ms) -> str:
    """Pure (0D.3, information only): where a page-clock time lies relative to the tab click."""
    if not (_num(t_page_ms) and _num(before_ms) and _num(after_ms)):
        return "unknown"
    if t_page_ms < before_ms:
        return "before_click"
    if t_page_ms > after_ms:
        return "after_click"
    return "during_click"


def page_hook_summary(obs: dict, scenario: str) -> dict:
    """Information for the JSON (0D.3), not a check: records of the page hook and CDP sockets by path, the owner and
    the click phase of each record of the tab_unmounted path."""
    page_ws = obs.get("ws_page")
    recs = [r for r in page_ws if isinstance(r, dict)] if isinstance(page_ws, list) else None
    n_records = None
    if recs is not None:
        n_records = {}
        for r in recs:
            path = _url_path(r.get("url"))
            n_records[path] = n_records.get(path, 0) + 1
    n_cdp: dict = {}
    for w in obs.get("ws") or []:
        path = _url_path(w.get("url"))
        n_cdp[path] = n_cdp.get(path, 0) + 1
    table = SCENARIO_WS_ROLES[scenario]
    owners, phases = [], []
    if table["tab_unmounted"] and recs is not None:
        tab = _single_step(obs.get("steps"), table["tab_step"]) or {}
        for r in recs:
            if _url_path(r.get("url")) == table["tab_unmounted"]:
                owners.append(ws_owner(r.get("frames")))
                phases.append(click_phase(r.get("t_page_ms"), tab.get("click_page_ms_before"),
                                          tab.get("click_page_ms_after")))
    return {"n_records_by_path": n_records, "n_cdp_by_path": n_cdp, "tab_unmounted_owners": owners,
            "tab_unmounted_click_phase": phases}


def evaluate(args, obs: dict, ready: dict, stop: dict, clip: dict) -> dict:
    checks: dict = {}
    h = ready.get("health") or {}
    check(checks, "health_200_status_ok_within_180s", ready["health_status"] == 200 and h.get("status") == "ok",
          {"http_status": ready["health_status"], "status": h.get("status"), "wait_s": ready["health_wait_s"]})
    check(checks, "page_3000_200_within_180s", ready["page_status"] == 200,
          {"http_status": ready["page_status"], "wait_s": ready["page_wait_s"]})
    if obs is None:
        check(checks, "browser_run", False, "no browser observations")
    else:
        check(checks, "browser_run_without_fatal_error", obs.get("fatal_error") is None, obs.get("fatal_error"))
        check(checks, "console_error_0", len(obs["console_errors"]) == 0, obs["console_errors"])
        check(checks, "pageerror_0", len(obs["page_errors"]) == 0, obs["page_errors"])
        check(checks, "requestfailed_0", len(obs["request_failed"]) == 0, obs["request_failed"])
        check(checks, "http_ge_400_0", len(obs["http_errors"]) == 0, obs["http_errors"])
        # AC12 revision 2 (0B.1): the Vite HMR socket is excluded from the "via /ws/" check only
        cls = classify_ws(obs["ws"])
        checks.update(cls["checks"])
        check(checks, "no_request_to_old_image_endpoint", len(obs["requests_old_image_endpoint"]) == 0,
              obs["requests_old_image_endpoint"])
    check(checks, "ports_8000_3000_free_after_stop", not any(stop["ports_listening_after_stop"].values()),
          stop["ports_listening_after_stop"])
    check(checks, "no_child_process_left", not stop["processes_alive_after_stop"], stop["processes_alive_after_stop"])

    if obs is None:
        return checks
    ws_by_path = app_ws_by_path(obs["ws"])
    # AC12 revision 3 (0C.2): StrictMode orphan rule (0B.2) on the `used` path of the scenario only;
    # tab_unmounted_socket_rule on every other app path
    checks.update(scenario_ws_roles(ws_by_path, args.scenario, obs.get("steps"))["checks"])
    # AC12 revision 4 (0D.3): source of the sockets of the tab_unmounted path (page hook of e2e_browser.cjs)
    owner = tab_unmounted_owner_check(ws_by_path, obs.get("ws_page"), args.scenario)
    check(checks, "tab_unmounted_owner_rule", owner["pass"], owner["detail"])

    if args.scenario == "fingerspell":
        st = obs.get("fingerspelling_status") or {}
        check(checks, "status_available_true", st.get("available") is True and obs["dom"].get("fs_status_available") == "true",
              {"api": st, "fs_status_data_available": obs["dom"].get("fs_status_available")})
        hws = ws_by_path.get("/ws/hand-landmarks", [])
        # every socket but a StrictMode orphan (0B.2) must receive session_info first
        ho = strictmode_orphans(hws)
        check(checks, "hand_ws_session_info",
              bool(ho["checked"]) and all(w["first_type"] == "session_info" for w in ho["checked"]),
              {"orphans": ho["orphans"],
               "sockets": [{"first_type": w["first_type"], "count_by_type": w["count_by_type"], "closed": w["closed"]}
                           for w in hws]})
        seq = obs["sequence_posts"]
        ok200 = [p for p in seq if p["status"] == 200]
        check(checks, "sequence_post_200_at_least_1", len(ok200) >= 1, [p["status"] for p in seq])
        body_problems = []
        for i, p in enumerate(seq):
            f = p["body_facts"] or {}
            probs = []
            if "parse_error" in f:
                probs.append("unparsable body")
            else:
                n = f["n_landmarks"]
                if not (n == f["n_handedness"] == f["n_timestamps_ms"] and n <= MAX_SEQUENCE_FRAMES):
                    probs.append("lengths")
                if f["n_non_null_frames"] < 3:
                    probs.append("fewer than 3 non-null frames")
                if f["n_frames_21_identical_points"] or f["n_frames_all_zero"]:
                    probs.append("frame with 21 identical points")
                if f["n_frames_bad_shape"] or f["n_non_finite_values"] or f["max_abs_value"] > MAX_ABS_VALUE:
                    probs.append("shape / finite / |v| <= 10")
                if not f["timestamps_non_decreasing"]:
                    probs.append("timestamps decrease")
                if f["source_mirrored"] is not False:
                    probs.append("source_mirrored is not false")
            if probs:
                body_problems.append({"post": i, "problems": probs})
        check(checks, "every_sequence_body_valid", len(seq) >= 1 and not body_problems, body_problems)
        last = seq[-1] if seq else None
        resp = (last or {}).get("response") or {}
        dom = obs["dom"]
        check(checks, "fs_prediction_equals_last_response", last is not None and last["status"] == 200
              and dom.get("fs_prediction") == str(resp.get("prediction")),
              {"dom": dom.get("fs_prediction"), "response": resp.get("prediction")})
        check(checks, "fs_confidence_shows_response_confidence",
              dom.get("expected_confidence_value") is not None
              and dom.get("fs_confidence_value") == dom.get("expected_confidence_value")
              and dom.get("fs_confidence_text") == dom.get("expected_confidence_text"),
              {"dom_value": dom.get("fs_confidence_value"), "dom_text": dom.get("fs_confidence_text"),
               "expected_value": dom.get("expected_confidence_value"),
               "expected_text": dom.get("expected_confidence_text")})
        comp = obs["compose_posts"]
        lastc = comp[-1] if comp else None
        ctext = ((lastc or {}).get("response") or {}).get("text")
        check(checks, "fs_add_compose_200_and_text_shown", lastc is not None and lastc["status"] == 200
              and isinstance(ctext, str) and dom.get("fs_composed") == ctext.strip(),
              {"status": (lastc or {}).get("status"), "tokens": (lastc or {}).get("tokens"),
               "response_text": ctext, "dom": dom.get("fs_composed")})
    else:
        lws = ws_by_path.get("/ws/live-stream", [])
        w = lws[-1] if lws else None
        # every socket but a StrictMode orphan (0B.2) must receive session_info first
        lo = strictmode_orphans(lws)
        si = (w or {}).get("session_info") or {}
        want_pipeline = "harmonized_v1" if args.model_type == "stgcn_h360" else "legacy"
        check(checks, "live_ws_first_message_session_info_v2",
              w is not None and w["first_type"] == "session_info" and si.get("protocol_version") == 2
              and si.get("pipeline") == want_pipeline
              and bool(lo["checked"]) and all(x["first_type"] == "session_info" for x in lo["checked"]),
              {"first_type": (w or {}).get("first_type"), "protocol_version": si.get("protocol_version"),
               "pipeline": si.get("pipeline"), "sockets": len(lws), "orphans": lo["orphans"],
               "sockets_first_types": [x["first_type"] for x in lws]})
        errors = [e for x in lws for e in x["errors"]]
        check(checks, "ws_error_messages_0", w is not None and not errors, errors)
        dom = obs["dom"]
        check(checks, "live_pipeline_shown", dom.get("live_pipeline") == want_pipeline, dom.get("live_pipeline"))
        fr = (w or {}).get("frame_result") or {}
        n_fr = (w or {}).get("count_by_type", {}).get("frame_result", 0)
        if want_pipeline == "legacy":
            check(checks, "frame_result_at_least_30", n_fr >= 30, n_fr)
            lf = (w or {}).get("last_frame_result") or {}
            check(checks, "live_top5_equals_last_frame_result_top5",
                  obs.get("quiet_after_stop") is True and dom.get("live_top5") == lf.get("top5_js_strings"),
                  {"quiet_after_stop": obs.get("quiet_after_stop"), "dom": dom.get("live_top5"),
                   "last_frame_result": lf.get("top5_js_strings")})
        else:
            check(checks, "every_frame_result_prediction_null",
                  n_fr > 0 and fr.get("prediction_non_null") == 0 and fr.get("prediction_key_missing") == 0,
                  {"frame_results": n_fr, "non_null": fr.get("prediction_non_null"),
                   "key_missing": fr.get("prediction_key_missing")})
            n_rec = (fr.get("status_counts") or {}).get("RECORDING", 0)
            check(checks, "frame_result_recording_at_least_1", n_rec >= 1, fr.get("status_counts"))
            check(checks, "live_recording_shown_at_least_once", (dom.get("live_recording_appearances") or 0) >= 1,
                  dom.get("live_recording_appearances"))
            n_ev = len(w["sign_results"]) + len(w["sign_discarded"]) if w else 0
            check(checks, "sign_event_within_max_loops", n_ev >= 1 and obs.get("ran_loops", 99) <= args.max_loops,
                  {"sign_result": len(w["sign_results"]) if w else 0,
                   "sign_discarded": len(w["sign_discarded"]) if w else 0, "ran_loops": obs.get("ran_loops")})
            if w and w["sign_results"]:
                ls = w["sign_results"][-1]
                check(checks, "live_gloss_and_top5_equal_last_sign_result",
                      obs.get("quiet_after_stop") is True and dom.get("live_gloss") == ls["gloss"]
                      and dom.get("live_top5") == ls["top5_js_strings"],
                      {"dom_gloss": dom.get("live_gloss"), "gloss": ls["gloss"], "dom_top5": dom.get("live_top5"),
                       "top5": ls["top5_js_strings"]})
    return checks


def ws_classification(obs, scenario: str) -> dict:
    """JSON summary (0B.1 / 0B.2 / 0C.2 / 0D.3): the Vite HMR socket(s) excluded from the "via /ws/" check, the role
    of each app path, the number of StrictMode orphans on the `used` path, the number of sockets on the
    `tab_unmounted` path, and page_hook (information only, not a check)."""
    if obs is None:
        return None
    roles = scenario_ws_roles(app_ws_by_path(obs["ws"]), scenario, obs.get("steps"))
    used = SCENARIO_WS_ROLES[scenario]["used"]
    return {"vite_hmr_excluded": classify_ws(obs["ws"])["hmr_excluded"],
            "role_by_path": roles["role_by_path"],
            "strictmode_orphans_by_path": {used: len(roles["strictmode_used"]["orphans"])},
            "tab_unmounted_by_path": roles["tab_unmounted_by_path"],
            "page_hook": page_hook_summary(obs, scenario)}


def _find_forbidden(obj, path="") -> list:
    bad = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("landmarks", "raw_landmarks", "coords"):
                bad.append(f"{path}/{k}")
            bad += _find_forbidden(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            bad += _find_forbidden(v, f"{path}[{i}]")
    return bad


# ----------------------------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Plan 06 AC12 end-to-end run (see the module docstring).")
    ap.add_argument("--scenario", choices=("fingerspell", "word"), required=True)
    ap.add_argument("--model-type", default=None, help="VSL_MODEL_TYPE for this run only (e.g. stgcn_h360)")
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-loops", type=int, default=3)
    ap.add_argument("--tmp-dir", default=os.path.join(tempfile.gettempdir(), "vslt_e2e"),
                    help="Y4M + logs; must be outside the repository")
    args = ap.parse_args(argv)
    if make_fake_webcam_y4m.is_inside_repo(args.tmp_dir):
        raise SystemExit("--tmp-dir must be outside the repository")
    os.makedirs(args.tmp_dir, exist_ok=True)

    command = ("PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/e2e_fullstack.py --scenario " + args.scenario
               + (f" --model-type {args.model_type}" if args.model_type else "")
               + f" --video {_rel(args.video)} --out {_rel(args.out)}"
               + (f" --max-loops {args.max_loops}" if args.max_loops != 3 else ""))
    generated_by = {
        "command": command,
        "git_commit": _git("rev-parse", "HEAD"),
        "code_dirty": bool(_git("status", "--porcelain", "--", *CODE_PATHS)),
        "code_dirty_paths": list(CODE_PATHS),
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    clip = clip_identity(args.video)
    vf = video_facts(args.video)

    busy = {p: v for p, v in _ports_listening().items() if v}
    if busy:
        raise SystemExit(f"ports already in use before the run: {sorted(busy)} (nothing was started or killed)")

    tag = args.scenario + (f"_{args.model_type}" if args.model_type else "_default")
    y4m_path = os.path.join(args.tmp_dir, f"{clip['clip_id']}.y4m")
    y4m = make_fake_webcam_y4m.write_y4m(args.video, y4m_path)
    clip_seconds = y4m["frames"] * y4m["fps_den"] / y4m["fps_num"]

    env = dict(os.environ)
    env.pop("VSL_CORS_ORIGINS", None)
    env.pop("VSL_MODEL_TYPE", None)
    if args.model_type:
        env["VSL_MODEL_TYPE"] = args.model_type
    env["PYTHONIOENCODING"] = "utf-8"

    stack_log = os.path.join(args.tmp_dir, f"{tag}_stack.log")
    browser_out = os.path.join(args.tmp_dir, f"{tag}_browser.json")
    browser_log = os.path.join(args.tmp_dir, f"{tag}_browser.log")
    if os.path.exists(browser_out):
        os.remove(browser_out)
    t0 = time.monotonic()
    proc = start_stack(env, stack_log)
    obs = None
    browser_exit = None
    ready = {"health_status": None, "health": None, "health_wait_s": None, "page_status": None, "page_wait_s": None}
    try:
        ready = wait_ready(t0)
        if ready["health_status"] == 200 and ready["page_status"] == 200:
            node = shutil.which("node") or "node"
            with open(browser_log, "wb") as bl:
                r = subprocess.run([node, os.path.join(ROOT, "scripts", "e2e_browser.cjs"),
                                    "--scenario", args.scenario, "--y4m", y4m_path, "--out", browser_out,
                                    "--clip-seconds", f"{clip_seconds:.6f}", "--max-loops", str(args.max_loops)],
                                   cwd=ROOT, stdout=bl, stderr=subprocess.STDOUT, timeout=600)
            browser_exit = r.returncode
            if os.path.exists(browser_out):
                with open(browser_out, encoding="utf-8") as f:
                    obs = json.load(f)
    finally:
        stop = stop_stack(proc)

    checks = evaluate(args, obs, ready, stop, clip)
    node_version = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
    result = {
        "generated_by": generated_by,
        "plan": "docs/plans/06-viec5-frontend.md AC12",
        "note": NOTE,
        "scenario": args.scenario,
        "model_type_env": args.model_type,
        "versions": {"node": node_version, "browser": (obs or {}).get("browser_version"),
                     "mediapipe": importlib.metadata.version("mediapipe"), "python": sys.version.split()[0]},
        "clip": {**clip, "video": _rel(args.video), "video_facts": vf,
                 "y4m": {k: y4m[k] for k in ("frames", "width", "height", "fps_num", "fps_den")},
                 "clip_loop_seconds": round(clip_seconds, 4)},
        "startup": ready,
        "health": {"model_type": (ready.get("health") or {}).get("model_type"),
                   "is_default": (ready.get("health") or {}).get("is_default_model"),
                   "pipeline": (ready.get("health") or {}).get("pipeline")},
        "shutdown": stop,
        "browser_exit_code": browser_exit,
        "observations": obs,
        "ws_classification": ws_classification(obs, args.scenario),
        "checks": checks,
    }
    if obs is not None and args.scenario == "fingerspell":
        seq = obs["sequence_posts"]
        resp = (seq[-1].get("response") or {}) if seq else {}
        result["info_not_accuracy"] = {"clip_id": clip["clip_id"], "clip_label": clip["label"],
                                       "prediction": resp.get("prediction"), "confidence": resp.get("confidence")}
    elif obs is not None:
        lws = app_ws_by_path(obs["ws"]).get("/ws/live-stream", [])
        w = lws[-1] if lws else {}
        result["info_not_accuracy"] = {
            "clip_id": clip["clip_id"], "clip_label": clip["label"],
            "last_frame_result_gloss": (w.get("last_frame_result") or {}).get("gloss"),
            "sign_result_glosses": [s["gloss"] for s in w.get("sign_results", [])],
            "sign_discarded_reasons": [s["reason"] for s in w.get("sign_discarded", [])],
        }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    raw = {ROOT, ROOT.replace("\\", "/"), os.path.abspath(args.tmp_dir), os.path.expanduser("~")}
    needles = {x for s in raw if s for x in (s, json.dumps(s)[1:-1])}
    leaks = [s for s in needles if s in text]
    forbidden = _find_forbidden(result)
    check(checks, "json_has_no_absolute_path_landmark_or_image", not leaks and not forbidden
          and "data:image" not in text, {"path_leaks": len(leaks), "forbidden_keys": forbidden})
    check(checks, "code_clean_at_run", generated_by["code_dirty"] is False, generated_by["code_dirty"])
    result["all_checks_pass"] = all(c["pass"] for c in checks.values())
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if leaks:  # never write an absolute path into the report
        for s in sorted(leaks, key=len, reverse=True):
            text = text.replace(s, "<redacted>")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")
    failed = [k for k, c in checks.items() if not c["pass"]]
    print(f"wrote {_rel(args.out)}: scenario={args.scenario} model_type={args.model_type or 'default'} "
          f"checks {len(checks) - len(failed)}/{len(checks)} pass" + (f"; FAILED: {failed}" if failed else ""))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
