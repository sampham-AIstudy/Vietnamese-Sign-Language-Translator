"""
Plan 10 - DoD 7 source guard, backend / Python side (docs/plans/10-guard-dod7.md).

Static AST guard. Standard library only: it never imports torch / numpy / cv2 / mediapipe / fastapi / backend.main or
any module of src/ (files are only READ as text and parsed with `ast`).

Scope (plan 10 §3.1):
  SERVING = static import closure of ENTRYPOINTS (backend/main.py = the uvicorn target of start_fullstack.ps1,
            realtime_demo.py = the desktop realtime demo of README §5.4), recomputed on every run.
  MAIN    = backend/**/*.py + src/**/*.py + SERVING.
Rules (plan 10 §3.3; each finding carries exactly one code):
  A-stdlib / A-numpy / A-torch   unseeded RNG                         (SERVING)
  B-import / B-name              mock libraries                        (MAIN)
  C-name / C-string / C-result   fake / simulated data or results      (SERVING)
  D-binding / D-string           hand-typed performance numbers        (MAIN)
Findings are grouped by (path, rule, qualname) and compared with two registries (plan 10 §3.4-§3.6):
  ALLOWED           false positives approved by the planner (keys limited to PLAN10_APPROVED_ALLOWED);
  KNOWN_VIOLATIONS  pre-existing violations, copied from the guard's own first output (B1). It may only SHRINK.
A new group, a group whose count changed, or a registered group that disappeared makes the test FAIL.
DoD 7 (backend part) is PASS only when KNOWN_VIOLATIONS is empty.

Run:    PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_backend_source_guard -v
Report: PYTHONIOENCODING=utf-8 .venv/bin/python -m tests.test_backend_source_guard --report \
        reports/guard_dod7_<YYYY-MM-DD>/guard_findings.json
"""
import ast
import collections
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ----------------------------------------------------------------------------------------------------------------------
# Scope (plan 10 §3.1)
# ----------------------------------------------------------------------------------------------------------------------
ENTRYPOINTS = ("backend/main.py", "realtime_demo.py")
# scripts/ files on the serving path: static imports of SERVING + scripts called by start_fullstack.ps1 (plan 10 §2.4).
SCRIPTS_REALTIME = ()
# Anti empty-pass: a broken resolver would return a small set.
MIN_SERVING = (
    "backend/main.py",
    "realtime_demo.py",
    "src/inference/predictor.py",
    "src/inference/realtime_pipeline.py",
    "src/inference/harmonized_live.py",
    "src/inference/hand_live.py",
    "src/inference/sign_segmenter.py",
    "src/inference/fingerspelling_compose.py",
    "src/data/harmonized.py",
    "src/data/alphabet_preprocessing.py",
    "src/models/alphabet_temporal.py",
    "src/translation/end_to_end.py",
    "src/translation/translator.py",
)
NOT_SERVING = ("src/training/trainer.py", "src/export/export_onnx.py")
UVICORN_TARGET = "backend.main:app"
_PS1_SCRIPT_RX = re.compile(r"scripts[\\/][\w.-]+\.py")

# ----------------------------------------------------------------------------------------------------------------------
# Rules (plan 10 §3.3)
# ----------------------------------------------------------------------------------------------------------------------
RULES = ("A-stdlib", "A-numpy", "A-torch", "B-import", "B-name",
         "C-name", "C-string", "C-result", "D-binding", "D-string")
ALL_RULES = frozenset(RULES)
MAIN_RULES = frozenset({"B-import", "B-name", "D-binding", "D-string"})  # MAIN files outside SERVING
_RULE_ORDER = {r: i for i, r in enumerate(RULES)}

RULE_DESCRIPTIONS = {
    "A-stdlib": "SERVING: unseeded stdlib random draw (random.<f>, Random()/Random(None), seed()/seed(None), "
                "SystemRandom) not preceded by random.seed(<not None>) in the same function scope",
    "A-numpy": "SERVING: numpy global-state draw (numpy.random.<f>) not preceded by numpy.random.seed(<not None>) in "
               "the same scope; default_rng/RandomState/seed/bit generator called without a seed or with None",
    "A-torch": "SERVING: torch.<rand...>/normal/bernoulli/multinomial/poisson/seed or in-place <t>.uniform_()... "
               "without generator= and not after torch.manual_seed(<not None>) in the same scope "
               "(torch.nn.init.* excluded); torch.Generator() never manual_seed-ed in the same scope",
    "B-import": "MAIN: import of a mock library (unittest.mock, mock, pytest_mock, asynctest)",
    "B-name": "MAIN: use of Mock / MagicMock / AsyncMock / NonCallableMock / NonCallableMagicMock / PropertyMock / "
              "create_autospec / mock_open, or <...mock>.patch",
    "C-name": "SERVING: name binding (assignment/for/with/def/class/parameter/import alias) with a fake/dummy/mock/"
              "stub/simulated/synthetic/placeholder/fabricated token",
    "C-string": "SERVING: string (non-docstring, or FastAPI route docstring) saying fake/dummy/mock/stub/simulated/"
                "synthetic/placeholder/fabricated or 'giả lập'/'dữ liệu giả'/'kết quả giả'/'số liệu giả'",
    "C-result": "SERVING: fixed literal bound to a result key/name (gloss, prediction, translation, confidence, top5, "
                "...) or returned by a predict/translate/classify/recognize/infer function",
    "D-binding": "MAIN: metric-named binding (accuracy/top1/f1/wer/bleu/latency/fps/ms/...) receiving a hand-typed "
                 "number or a hand-typed ratio (x * 0.4)",
    "D-string": "MAIN: string (non-docstring, or FastAPI route docstring) with a percentage, a number with ms/fps, or "
                "a metric keyword followed by a number",
}

Finding = collections.namedtuple("Finding", "path line rule qualname snippet")

SENTINELS = frozenset({0, -1})
UNIT_FACTORS = frozenset({1, 100, 1000, 1_000_000, 0.01, 0.001, 1e-6, 60, 3600})
_NUMSTR_RX = re.compile(r"^\s*[-+]?\d+(?:[.,]\d+)?\s*%?\s*$")
_WORD_RX = re.compile(r"\w")

STDLIB_DRAWS = frozenset({
    "random", "randint", "randrange", "choice", "choices", "shuffle", "sample", "uniform", "triangular", "gauss",
    "normalvariate", "lognormvariate", "expovariate", "vonmisesvariate", "gammavariate", "betavariate",
    "paretovariate", "weibullvariate", "binomialvariate", "getrandbits", "randbytes",
})
NUMPY_NON_GLOBAL = frozenset({"default_rng", "Generator", "SeedSequence", "RandomState", "seed", "BitGenerator",
                              "PCG64", "PCG64DXSM", "MT19937", "Philox", "SFC64"})
NUMPY_NEEDS_SEED = frozenset({"default_rng", "RandomState", "seed", "BitGenerator",
                              "PCG64", "PCG64DXSM", "MT19937", "Philox", "SFC64"})
TORCH_DRAWS = frozenset({"rand", "randn", "randint", "randperm", "rand_like", "randn_like", "randint_like", "normal",
                         "bernoulli", "multinomial", "poisson", "seed"})
TORCH_INPLACE = frozenset({"uniform_", "normal_", "bernoulli_", "random_", "exponential_", "geometric_", "cauchy_",
                           "log_normal_"})
TORCH_INIT = "torch.nn.init"

MOCK_MODULES = ("unittest.mock", "mock", "pytest_mock", "asynctest")
MOCK_NAMES = frozenset({"Mock", "MagicMock", "AsyncMock", "NonCallableMock", "NonCallableMagicMock", "PropertyMock",
                        "create_autospec", "mock_open"})

FAKE_TOKENS = frozenset({"fake", "dummy", "mock", "mocked", "stub", "simulate", "simulated", "simulation",
                         "simulator", "synthetic", "synthesized", "synthesised", "placeholder", "fabricated"})
C_STRING_RXS = (
    re.compile(r"(?i)\b(fake|dummy|mock(?:ed)?|stub(?:bed)?|simulat(?:e|ed|ion|or)|synthe(?:tic|sized|sised)"
               r"|placeholder|fabricated)\b"),
    re.compile(r"(?i)giả\s+lập|dữ\s+liệu\s+giả|kết\s+quả\s+giả|số\s+liệu\s+giả"),
)
RESULT_KEYS = frozenset({"gloss", "glosses", "prediction", "predictions", "translation", "translated_text",
                         "confidence", "top5", "candidates", "sentence"})
RESULT_LAST_TOKENS = frozenset({"gloss", "glosses", "prediction", "predictions", "translation", "confidence"})
INFER_FUNC_TOKENS = frozenset({"predict", "translate", "classify", "recognize", "recognise", "infer"})

METRIC_TOKENS = frozenset({"accuracy", "acc", "top1", "top5", "topk", "precision", "recall", "f1", "wer", "cer", "bleu",
                           "rouge", "meteor", "latency", "fps", "throughput", "speedup", "p50", "p90", "p95", "p99",
                           "ms"})
D_STRING_RXS = (
    re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?\s*%"),
    re.compile(r"(?i)(?<![\w.])\d+(?:[.,]\d+)?\s*(?:ms|fps)\b"),
    re.compile(r"(?i)\b(?:accuracy|acc|top-?[15]|precision|recall|f1|wer|cer|bleu|rouge|latency|fps|throughput"
               r"|độ\s+chính\s+xác|độ\s+trễ)\b[^\d\n]{0,20}(?<![\w-])\d"),
)
ROUTE_METHODS = frozenset({"get", "post", "put", "patch", "delete", "websocket", "api_route"})

REPORT_NOTE = "static source guard for DoD 7; counts are code findings, not model metrics"

# ----------------------------------------------------------------------------------------------------------------------
# Registries (plan 10 §3.6). Key = (path, rule, qualname); value = (count, text).
# ----------------------------------------------------------------------------------------------------------------------
_AUGMENT_METHODS = ("add_jitter", "random_scale", "random_rotate_2d", "time_warp", "keypoint_mask",
                    "augment_sequence", "augment_static", "augment_vsl_sequence")
# Exactly the 16 keys of the plan 10 §3.6 table. Only a planner "Lần sửa" may change this constant.
PLAN10_APPROVED_ALLOWED = frozenset(
    [("src/data/augment.py", "A-numpy", "KeypointAugmenter." + m) for m in _AUGMENT_METHODS] + [
        ("src/data/harmonized.py", "A-torch", "HarmonizedDataset.__getitem__"),
        ("src/data/harmonized.py", "D-binding", "HarmonizedDataset.__getitem__"),
        ("src/data/harmonized.py", "D-binding", "harmonize"),
        ("src/metrics/cslr_metrics.py", "D-binding", "compute_wer"),
        ("src/data/vsl_dataset.py", "D-string", "validate_split_guards"),
        ("src/inference/ensemble.py", "D-string", "run_ensemble_benchmark"),
        ("src/inference/predictor.py", "C-name", "VSLPredictor.warmup"),
        ("src/inference/realtime_extractor.py", "C-name", "RealtimeLandmarkExtractor.__init__"),
    ])

# ALLOWED = the keys of PLAN10_APPROVED_ALLOWED reported by the first raw scan (B1); counts copied from that output.
_AUGMENT_TEXT = ("augmentation lúc train; chỉ tạo khi augment=True; module vào bao đóng phục vụ qua import đầu "
                 "module src/inference/ensemble.py -> src/data/vsl_dataset.py, không hàm phục vụ nào gọi")

ALLOWED = {
    ('src/data/augment.py', 'A-numpy', 'KeypointAugmenter.add_jitter'): (
        1, _AUGMENT_TEXT),
    ('src/data/augment.py', 'A-numpy', 'KeypointAugmenter.augment_sequence'): (
        5, _AUGMENT_TEXT),
    ('src/data/augment.py', 'A-numpy', 'KeypointAugmenter.augment_static'): (
        3, _AUGMENT_TEXT),
    ('src/data/augment.py', 'A-numpy', 'KeypointAugmenter.augment_vsl_sequence'): (
        12, _AUGMENT_TEXT),
    ('src/data/augment.py', 'A-numpy', 'KeypointAugmenter.keypoint_mask'): (
        2, _AUGMENT_TEXT),
    ('src/data/augment.py', 'A-numpy', 'KeypointAugmenter.random_rotate_2d'): (
        1, _AUGMENT_TEXT),
    ('src/data/augment.py', 'A-numpy', 'KeypointAugmenter.random_scale'): (
        1, _AUGMENT_TEXT),
    ('src/data/augment.py', 'A-numpy', 'KeypointAugmenter.time_warp'): (
        1, _AUGMENT_TEXT),
    ('src/data/harmonized.py', 'A-torch', 'HarmonizedDataset.__getitem__'): (
        1, 'nhánh augment của Dataset train; live gọi harmonize(rng=None)'),
    ('src/data/harmonized.py', 'D-binding', 'HarmonizedDataset.__getitem__'): (
        1, 'fps ĐẦU VÀO mặc định khi npz thiếu metadata; không phải số đo'),
    ('src/data/harmonized.py', 'D-binding', 'harmonize'): (
        1, 'fps ĐẦU VÀO mặc định; tham số tiền xử lý dùng chung'),
    ('src/data/vsl_dataset.py', 'D-string', 'validate_split_guards'): (
        1, 'câu báo lỗi kiểm toàn vẹn split ("100% dialect")'),
    ('src/inference/ensemble.py', 'D-string', 'run_ensemble_benchmark'): (
        1, 'mô tả trọng số 0.5/0.5 của hàm đánh giá offline'),
    ('src/inference/predictor.py', 'C-name', 'VSLPredictor.warmup'): (
        3, 'tensor warmup, đầu ra bỏ (_ = self.model(...))'),
    ('src/inference/realtime_extractor.py', 'C-name', 'RealtimeLandmarkExtractor.__init__'): (
        1, 'khung warmup MediaPipe, đầu ra bỏ'),
    ('src/metrics/cslr_metrics.py', 'D-binding', 'compute_wer'): (
        1, 'quy ước công thức WER khi không có từ tham chiếu'),
}

# Pre-existing violations = every other group of the first raw scan (B1, /home/user/_plan10_tmp/b1_first_scan.json at
# HEAD 5b979a5). Counts copied from that output by a script, not typed. This registry may only SHRINK (plan 10 §3.5).
KNOWN_VIOLATIONS = {
    ('realtime_demo.py', 'C-result', 'RealtimeHUD._locate_vietnamese_font'): (
        1, "đề xuất DTG (planner xét): 'candidates' là danh sách đường dẫn font, không phải kết quả nhận dạng; "
           "hướng sửa nếu không duyệt: đổi tên biến (ví dụ font_paths) — kế hoạch sau"),
    ('realtime_demo.py', 'C-string', 'RealtimeDemo._open_stream'): (
        2, "nguồn giả '--source mock' (khung tổng hợp) trong điểm vào người dùng; hướng sửa: bỏ chế độ mock khỏi "
           "realtime_demo.py (hoặc chuyển thành fixture chỉ trong tests/) — kế hoạch sau"),
    ('realtime_demo.py', 'C-string', 'RealtimeDemo.run'): (
        1, "nhánh vẽ khung giả khi source == 'mock'; hướng sửa: bỏ cùng chế độ mock — kế hoạch sau"),
    ('realtime_demo.py', 'C-string', 'main'): (
        1, "help của --source quảng cáo 'mock'; hướng sửa: bỏ cùng chế độ mock — kế hoạch sau"),
    ('realtime_demo.py', 'D-binding', 'RealtimeDemo.run'): (
        1, "avg_fps '... else 30.0' là FPS gõ tay hiển thị trên HUD; hướng sửa: hiển thị '—'/0 khi chưa đo "
           "— kế hoạch sau"),
    ('src/data/landmark_extractor.py', 'D-binding', 'CleanHolisticExtractor.extract_from_video'): (
        1, "đề xuất DTG (planner xét): 'or 25.0' là fps ĐẦU VÀO mặc định khi video thiếu metadata, không phải "
           "số đo; hướng sửa nếu không duyệt: hằng có tên/tham số cấu hình — kế hoạch sau"),
    ('src/data/vsl_gh_dataset.py', 'D-string', '<module>'): (
        1, "đề xuất DTG (planner xét): chuỗi ghi chú cấp module (sau import, không phải docstring) nói thứ tự "
           "landmark '100% identical', không phải số đo; hướng sửa nếu không duyệt: chuyển thành comment "
           "— kế hoạch sau"),
    ('src/inference/sign_segmenter.py', 'D-binding', 'SignSegmenter._activity'): (
        1, "đề xuất DTG (planner xét): fps suy từ timestamp; '30.0' chỉ dùng khi n < 2 (tốc độ = 0 bất kể fps), "
           "không phải số đo hiển thị; hướng sửa nếu không duyệt: hằng có tên — kế hoạch sau"),
}


# ----------------------------------------------------------------------------------------------------------------------
# AST helpers
# ----------------------------------------------------------------------------------------------------------------------
_TOKEN_RX = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")


def name_tokens(name):
    """Identifier -> lower-case tokens (split on '_' and camelCase; 'top_1'/'top1' -> 'top1'; 'bleu_4' -> bleu, 4)."""
    raw = []
    for part in name.split("_"):
        raw += [t.lower() for t in _TOKEN_RX.findall(part)]
    out = []
    for tok in raw:
        if tok.isdigit() and out and out[-1].isalpha() and 1 <= len(out[-1]) <= 3:
            out[-1] = out[-1] + tok
        else:
            out.append(tok)
    return out


def _token_in(tok, vocab):
    """Token membership with the plural rule ('...s' -> '...'; '...ies' -> '...y')."""
    if tok in vocab:
        return True
    if tok.endswith("s") and tok[:-1] in vocab:
        return True
    return tok.endswith("ies") and tok[:-3] + "y" in vocab


def _any_token_in(name, vocab):
    return any(_token_in(t, vocab) for t in name_tokens(name))


def _num_value(node):
    """Value of a numeric literal (Constant or +/- Constant, bool excluded), else None."""
    if isinstance(node, ast.Constant):
        v = node.value
        if isinstance(v, (int, float, complex)) and not isinstance(v, bool):
            return v
        return None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _num_value(node.operand)
        if v is None:
            return None
        return -v if isinstance(node.op, ast.USub) else v
    return None


def _is_const_num_expr(node):
    if _num_value(node) is not None:
        return True
    return isinstance(node, ast.BinOp) and _is_const_num_expr(node.left) and _is_const_num_expr(node.right)


def is_hand_typed(node):
    """H of plan 10 §3.3: a hand-typed number."""
    v = _num_value(node)
    if v is not None:
        return v not in SENTINELS
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and bool(_NUMSTR_RX.match(node.value))
    if isinstance(node, ast.BinOp):
        return _is_const_num_expr(node.left) and _is_const_num_expr(node.right)
    if isinstance(node, ast.IfExp):
        return is_hand_typed(node.body) or is_hand_typed(node.orelse)
    if isinstance(node, ast.BoolOp):
        return any(is_hand_typed(v) for v in node.values)
    return False


def has_hand_ratio(node):
    """A Mult/Div anywhere in the value with a numeric-literal operand outside UNIT_FACTORS (e.g. latency_ms * 0.4)."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.BinOp) and isinstance(sub.op, (ast.Mult, ast.Div)):
            for side in (sub.left, sub.right):
                v = _num_value(side)
                if v is not None and v not in UNIT_FACTORS:
                    return True
    return False


def is_fixed_value(node):
    """F of plan 10 §3.3 (C-result): a fixed literal result."""
    v = _num_value(node)
    if v is not None:
        return v not in SENTINELS
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and bool(_WORD_RX.search(node.value))
    if isinstance(node, (ast.List, ast.Tuple)):
        return bool(node.elts) and all(is_fixed_value(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return (bool(node.values) and all(k is not None for k in node.keys)
                and all(is_fixed_value(v) for v in node.values))
    return False


def _str_key(slice_node):
    if hasattr(ast, "Index") and isinstance(slice_node, getattr(ast, "Index")):  # Python < 3.9
        slice_node = slice_node.value
    if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
        return slice_node.value
    return None


def _dotted(node):
    """'a.b.c' for a Name/Attribute chain, else None (no alias resolution)."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    return ".".join([node.id] + parts[::-1])


def _has_non_none_arg(call):
    for a in call.args:
        if not (isinstance(a, ast.Constant) and a.value is None):
            return True
    for kw in call.keywords:
        if not (isinstance(kw.value, ast.Constant) and kw.value.value is None):
            return True
    return False


def _has_generator_kw(call):
    return any(kw.arg == "generator" for kw in call.keywords)


def _is_mock_module(name):
    return any(name == m or name.startswith(m + ".") for m in MOCK_MODULES)


def _is_route(func):
    for d in func.decorator_list:
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in ROUTE_METHODS:
            return True
    return False


def _collect_aliases(tree):
    """Local name -> dotted module path, from every Import/ImportFrom of the file (plan 10 §3.2)."""
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    aliases[a.asname] = a.name
                else:
                    top = a.name.split(".")[0]
                    aliases[top] = top
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for a in node.names:
                if a.name != "*":
                    aliases[a.asname or a.name] = node.module + "." + a.name
    return aliases


def _docstring_ids(tree):
    """ids of docstring Constants excluded from C-string / D-string (FastAPI route docstrings stay included)."""
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_route(node):
                    continue
                ids.add(id(first.value))
    return ids


class _Scanner(ast.NodeVisitor):
    """One pass over one file. qualname = enclosing class/def names joined by '.', '<module>' at top level; a def /
    class header (name, parameters, defaults) belongs to that def / class; decorators belong to the enclosing code.
    Scope for "seeded before" = innermost FunctionDef/AsyncFunctionDef (module scope otherwise)."""

    def __init__(self, tree, text, path, rules):
        self.path = path
        self.rules = rules
        self.lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self.aliases = _collect_aliases(tree)
        self.docstrings = _docstring_ids(tree)
        self.parents = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                self.parents[child] = parent
        self.stack = []
        self.scope = None
        self.findings = []
        self.pending_draws = []       # (scope, kind, Finding)
        self.seeds = collections.defaultdict(list)      # (scope, kind) -> [line]
        self.pending_generators = []  # (scope, [dotted target], Finding)
        self.seeded_objects = collections.defaultdict(set)  # scope -> {dotted name with .manual_seed(x)}

    # -- plumbing ------------------------------------------------------------------------------------------------------
    def _make(self, line, rule):
        snippet = self.lines[line - 1].strip()[:160] if 1 <= line <= len(self.lines) else ""
        return Finding(self.path, line, rule, ".".join(self.stack) if self.stack else "<module>", snippet)

    def _add(self, line, rule):
        if rule in self.rules:
            self.findings.append(self._make(line, rule))

    def _pending(self, line, rule, kind):
        if rule in self.rules:
            self.pending_draws.append((self.scope, kind, self._make(line, rule)))

    def run(self, tree):
        self.visit(tree)
        for scope, kind, f in self.pending_draws:
            if not any(seed_line < f.line for seed_line in self.seeds.get((scope, kind), ())):
                self.findings.append(f)
        for scope, names, f in self.pending_generators:
            if not any(n and n in self.seeded_objects.get(scope, ()) for n in names):
                self.findings.append(f)
        return sorted(self.findings, key=lambda f: (f.line, _RULE_ORDER[f.rule]))

    def _resolve(self, node):
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if not isinstance(node, ast.Name):
            return None
        base = self.aliases.get(node.id)
        if base is None:
            return None
        return ".".join([base] + parts[::-1])

    # -- C-name ------------------------------------------------------------------------------------------------------
    def _c_name(self, name, line):
        if "C-name" in self.rules and _any_token_in(name, FAKE_TOKENS):
            self._add(line, "C-name")

    # -- D-binding / C-result on a binding -----------------------------------------------------------------------------
    def _d_binding(self, label, value, line):
        if ("D-binding" in self.rules and label is not None and _any_token_in(label, METRIC_TOKENS)
                and (is_hand_typed(value) or has_hand_ratio(value))):
            self._add(line, "D-binding")

    def _binding(self, target, value, result_rules):
        name = key = None
        if isinstance(target, ast.Name):
            name = target.id
        elif isinstance(target, ast.Attribute):
            name = target.attr
        elif isinstance(target, ast.Subscript):
            key = _str_key(target.slice)
        line = target.lineno
        if result_rules and "C-result" in self.rules and is_fixed_value(value):
            toks = name_tokens(name) if name is not None else []
            if ((name is not None and ((toks and _token_in(toks[-1], RESULT_LAST_TOKENS)) or name in RESULT_KEYS))
                    or (key is not None and key in RESULT_KEYS)):
                self._add(line, "C-result")
        self._d_binding(name if name is not None else key, value, line)

    # -- definitions -------------------------------------------------------------------------------------------------
    def _visit_arguments(self, args):
        positional = list(getattr(args, "posonlyargs", [])) + list(args.args)
        every = positional + list(args.kwonlyargs) + [a for a in (args.vararg, args.kwarg) if a is not None]
        for a in every:
            self._c_name(a.arg, a.lineno)
            if a.annotation is not None:
                self.visit(a.annotation)
        pairs = list(zip(positional[len(positional) - len(args.defaults):], args.defaults))
        pairs += [(a, d) for a, d in zip(args.kwonlyargs, args.kw_defaults) if d is not None]
        for a, d in pairs:
            self._d_binding(a.arg, d, a.lineno)
            self.visit(d)

    def _visit_func(self, node):
        for d in node.decorator_list:
            self.visit(d)
        self.stack.append(node.name)
        self._c_name(node.name, node.lineno)
        self._visit_arguments(node.args)
        if node.returns is not None:
            self.visit(node.returns)
        outer, self.scope = self.scope, node
        for stmt in node.body:
            self.visit(stmt)
        self.scope = outer
        self.stack.pop()

    def visit_FunctionDef(self, node):
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_func(node)

    def visit_ClassDef(self, node):
        for d in node.decorator_list:
            self.visit(d)
        for b in node.bases:
            self.visit(b)
        for k in node.keywords:
            self.visit(k.value)
        self.stack.append(node.name)
        self._c_name(node.name, node.lineno)
        for stmt in node.body:
            self.visit(stmt)
        self.stack.pop()

    def visit_Lambda(self, node):
        self._visit_arguments(node.args)
        self.visit(node.body)

    # -- imports -------------------------------------------------------------------------------------------------------
    def visit_Import(self, node):
        if any(_is_mock_module(a.name) for a in node.names):
            self._add(node.lineno, "B-import")
        for a in node.names:
            if a.asname:
                self._c_name(a.asname, node.lineno)

    def visit_ImportFrom(self, node):
        if node.level == 0 and node.module:
            if _is_mock_module(node.module) or (node.module == "unittest"
                                                and any(a.name == "mock" for a in node.names)):
                self._add(node.lineno, "B-import")
        for a in node.names:
            if a.asname:
                self._c_name(a.asname, node.lineno)

    # -- names ---------------------------------------------------------------------------------------------------------
    def visit_Name(self, node):
        if node.id in MOCK_NAMES:
            self._add(node.lineno, "B-name")
        if isinstance(node.ctx, ast.Store):
            self._c_name(node.id, node.lineno)

    def visit_Attribute(self, node):
        if node.attr in MOCK_NAMES:
            self._add(node.lineno, "B-name")
        elif node.attr == "patch" and (
                (isinstance(node.value, ast.Name) and node.value.id == "mock")
                or (isinstance(node.value, ast.Attribute) and node.value.attr == "mock")):
            self._add(node.lineno, "B-name")
        if isinstance(node.ctx, ast.Store):
            self._c_name(node.attr, node.lineno)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.name:
            self._c_name(node.name, node.lineno)
        self.generic_visit(node)

    # -- bindings ------------------------------------------------------------------------------------------------------
    def visit_Assign(self, node):
        for t in node.targets:
            self._binding(t, node.value, result_rules=True)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if node.value is not None:
            self._binding(node.target, node.value, result_rules=True)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self._binding(node.target, node.value, result_rules=False)
        self.generic_visit(node)

    def visit_Dict(self, node):
        for k, v in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                if "C-result" in self.rules and k.value in RESULT_KEYS and is_fixed_value(v):
                    self._add(k.lineno, "C-result")
                self._d_binding(k.value, v, k.lineno)
        self.generic_visit(node)

    def visit_Return(self, node):
        if ("C-result" in self.rules and node.value is not None and self.scope is not None
                and _any_token_in(self.scope.name, INFER_FUNC_TOKENS) and is_fixed_value(node.value)):
            self._add(node.lineno, "C-result")
        self.generic_visit(node)

    # -- calls (A-* and D-binding keywords) ----------------------------------------------------------------------------
    def visit_Call(self, node):
        self._rng_call(node)
        for kw in node.keywords:
            if kw.arg:
                self._d_binding(kw.arg, kw.value, getattr(kw, "lineno", node.lineno))
        self.generic_visit(node)

    def _rng_call(self, node):
        line = node.lineno
        fq = self._resolve(node.func)
        seeded = _has_non_none_arg(node)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "manual_seed" and seeded:
            obj = _dotted(node.func.value)
            if obj:
                self.seeded_objects[self.scope].add(obj)
        if fq is not None:
            if fq.startswith("random.") and "." not in fq[len("random."):]:
                f = fq[len("random."):]
                if f == "seed":
                    if seeded:
                        self.seeds[(self.scope, "stdlib")].append(line)
                    else:
                        self._add(line, "A-stdlib")
                elif f in STDLIB_DRAWS:
                    self._pending(line, "A-stdlib", "stdlib")
                elif f == "Random" and not seeded:
                    self._add(line, "A-stdlib")
                elif f == "SystemRandom":
                    self._add(line, "A-stdlib")
            elif fq.startswith("numpy.random.") and "." not in fq[len("numpy.random."):]:
                f = fq[len("numpy.random."):]
                if f == "seed" and seeded:
                    self.seeds[(self.scope, "numpy")].append(line)
                elif f in NUMPY_NEEDS_SEED:
                    if not seeded:
                        self._add(line, "A-numpy")
                elif f not in NUMPY_NON_GLOBAL:
                    self._pending(line, "A-numpy", "numpy")
            elif fq.startswith("torch.") and "." not in fq[len("torch."):]:
                f = fq[len("torch."):]
                if f == "manual_seed":
                    if seeded:
                        self.seeds[(self.scope, "torch")].append(line)
                elif f in TORCH_DRAWS and not _has_generator_kw(node):
                    if f == "seed":
                        self._add(line, "A-torch")
                    else:
                        self._pending(line, "A-torch", "torch")
                elif f == "Generator":
                    self._generator(node)
        if (isinstance(node.func, ast.Attribute) and node.func.attr in TORCH_INPLACE
                and not _has_generator_kw(node) and self._resolve(node.func.value) != TORCH_INIT):
            self._pending(line, "A-torch", "torch")

    def _generator(self, node):
        if "A-torch" not in self.rules:
            return
        parent = self.parents.get(node)
        if isinstance(parent, ast.Attribute) and parent.attr == "manual_seed":
            grand = self.parents.get(parent)
            if isinstance(grand, ast.Call) and grand.func is parent and _has_non_none_arg(grand):
                return
        names = []
        if isinstance(parent, ast.Assign) and parent.value is node:
            names = [_dotted(t) for t in parent.targets]
        elif isinstance(parent, ast.AnnAssign) and parent.value is node:
            names = [_dotted(parent.target)]
        self.pending_generators.append((self.scope, names, self._make(node.lineno, "A-torch")))

    # -- strings (C-string / D-string) ---------------------------------------------------------------------------------
    def _string_unit(self, text, line):
        t = unicodedata.normalize("NFC", text)
        if "C-string" in self.rules and any(rx.search(t) for rx in C_STRING_RXS):
            self._add(line, "C-string")
        if "D-string" in self.rules and any(rx.search(t) for rx in D_STRING_RXS):
            self._add(line, "D-string")

    def visit_Constant(self, node):
        if isinstance(node.value, str) and id(node) not in self.docstrings:
            self._string_unit(node.value, node.lineno)

    def _visit_format_spec(self, spec):
        # the constant parts of a format spec ('.1f') are not strings; only the nested expressions are code
        for v in getattr(spec, "values", ()):
            if isinstance(v, ast.FormattedValue):
                self.visit(v.value)
                if v.format_spec is not None:
                    self._visit_format_spec(v.format_spec)

    def visit_JoinedStr(self, node):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            elif isinstance(v, ast.FormattedValue):
                parts.append("{}")
        self._string_unit("".join(parts), node.lineno)
        for v in node.values:
            if isinstance(v, ast.FormattedValue):
                self.visit(v.value)
                if v.format_spec is not None:
                    self._visit_format_spec(v.format_spec)


def scan_source(text, path, rules):
    """Pure function (no disk access): Finding list for `text` (reported as `path`) restricted to `rules`.
    SyntaxError propagates."""
    tree = ast.parse(text, filename=path)
    return _Scanner(tree, text, path, frozenset(rules)).run(tree)


# ----------------------------------------------------------------------------------------------------------------------
# Scope resolution
# ----------------------------------------------------------------------------------------------------------------------
def _rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _imported_modules(tree, relpath):
    """Candidate dotted modules imported anywhere in the file (lazy imports in function bodies included)."""
    parts = relpath[:-3].split("/")
    package = parts[:-1]
    mods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                p = a.name.split(".")
                mods += [".".join(p[:i]) for i in range(1, len(p) + 1)]
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if not node.module:
                    continue
                base = node.module.split(".")
            else:
                if not package or len(package) < node.level - 1:
                    continue
                base = package[:len(package) - (node.level - 1)] + (node.module.split(".") if node.module else [])
            if not base:
                continue
            mods += [".".join(base[:i]) for i in range(1, len(base) + 1)]
            mods += [".".join(base + [a.name]) for a in node.names if a.name != "*"]
    return mods


def _module_files(root, dotted):
    """Files Python runs for `import dotted`, looked up in <root> then <root>/scripts; [] for stdlib / third party."""
    parts = dotted.split(".")
    for base in (root, os.path.join(root, "scripts")):
        stem = os.path.join(base, *parts)
        for cand in (os.path.join(stem, "__init__.py"), stem + ".py"):
            if os.path.isfile(cand):
                files = [cand]
                for i in range(1, len(parts)):
                    init = os.path.join(base, *parts[:i], "__init__.py")
                    if os.path.isfile(init):
                        files.append(init)
                return files
    return []


def serving_closure(root, entrypoints):
    """Static import closure of `entrypoints` (relative paths, '/', sorted)."""
    seen = set()
    queue = list(entrypoints)
    while queue:
        rel = queue.pop()
        if rel in seen:
            continue
        seen.add(rel)
        tree = ast.parse(_read(os.path.join(root, rel)), filename=rel)
        for mod in _imported_modules(tree, rel):
            for f in _module_files(root, mod):
                r = _rel(root, f)
                if r not in seen:
                    queue.append(r)
    return sorted(seen)


def main_scope(root, serving):
    files = set(serving)
    for top in ("backend", "src"):
        for p in glob.glob(os.path.join(root, top, "**", "*.py"), recursive=True):
            r = _rel(root, p)
            if "__pycache__" not in r.split("/"):
                files.add(r)
    return sorted(files)


def scripts_realtime(root, serving):
    found = {p for p in serving if p.startswith("scripts/")}
    ps1 = os.path.join(root, "start_fullstack.ps1")
    if os.path.isfile(ps1):
        found |= {m.replace("\\", "/") for m in _PS1_SCRIPT_RX.findall(_read(ps1))}
    return sorted(found)


def scan_repo(root=PROJECT_ROOT):
    """(findings, scope) for the real tree: A/C rules on SERVING files, B/D rules on every MAIN file."""
    serving = serving_closure(root, ENTRYPOINTS)
    main = main_scope(root, serving)
    serving_set = set(serving)
    findings = []
    for rel in main:
        rules = ALL_RULES if rel in serving_set else MAIN_RULES
        findings += scan_source(_read(os.path.join(root, rel)), rel, rules)
    scope = {"entrypoints": list(ENTRYPOINTS), "serving_files": serving, "main_files": main,
             "scripts_realtime": scripts_realtime(root, serving)}
    return findings, scope


def rules_for(path, serving):
    return ALL_RULES if path in set(serving) else MAIN_RULES


def finding_key(f):
    return (f.path, f.rule, f.qualname)


def compare_registry(findings, allowed, known):
    """{'unregistered': [Finding], 'changed': [(key, registered, current)], 'stale': [(key, registered)]}."""
    counts = collections.Counter(finding_key(f) for f in findings)
    registered = dict(allowed)
    registered.update(known)
    unregistered = [f for f in findings if finding_key(f) not in registered]
    changed = [(k, registered[k][0], counts[k]) for k in sorted(registered)
               if counts.get(k, 0) > 0 and counts[k] != registered[k][0]]
    stale = [(k, registered[k][0]) for k in sorted(registered) if counts.get(k, 0) == 0]
    return {"unregistered": unregistered, "changed": changed, "stale": stale}


def format_comparison(cmp):
    lines = [f"{f.path}:{f.line}: {f.rule} [{f.qualname}] {f.snippet}" for f in cmp["unregistered"]]
    lines += [f"CHANGED {k[0]} {k[1]} {k[2]}: đăng ký {n}, hiện {m}" for k, n, m in cmp["changed"]]
    lines += [f"STALE {k[0]} {k[1]} {k[2]}: đăng ký {n}, hiện 0" for k, n in cmp["stale"]]
    return "\n".join(lines)


def registry_totals():
    return sum(c for c, _ in KNOWN_VIOLATIONS.values()), sum(c for c, _ in ALLOWED.values())


def _sort_key(f):
    return (f.path, f.line, _RULE_ORDER[f.rule], f.qualname, f.snippet)


_SCAN_CACHE = {}


def _cached_scan():
    if "repo" not in _SCAN_CACHE:
        _SCAN_CACHE["repo"] = scan_repo(PROJECT_ROOT)
    findings, scope = _SCAN_CACHE["repo"]
    return list(findings), dict(scope)


# ----------------------------------------------------------------------------------------------------------------------
# Report mode (plan 10 §3.7)
# ----------------------------------------------------------------------------------------------------------------------
def _git(*args):
    return subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True).stdout


def _command_line(argv):
    exe = os.path.abspath(sys.executable)
    try:
        rel = os.path.relpath(exe, PROJECT_ROOT)
    except ValueError:  # other drive on Windows
        rel = None
    python = rel.replace(os.sep, "/") if rel and not rel.startswith("..") else "python"
    enc = os.environ.get("PYTHONIOENCODING")
    prefix = f"PYTHONIOENCODING={enc} " if enc else ""
    return prefix + python + " -m tests.test_backend_source_guard " + " ".join(argv)


def build_report(command):
    findings, scope = scan_repo(PROJECT_ROOT)
    items = []
    by_status = {"known": 0, "allowed": 0, "unregistered": 0}
    by_rule = {r: 0 for r in RULES}
    for f in sorted(findings, key=_sort_key):
        key = finding_key(f)
        if key in KNOWN_VIOLATIONS:
            status, text = "known", KNOWN_VIOLATIONS[key][1]
        elif key in ALLOWED:
            status, text = "allowed", ALLOWED[key][1]
        else:
            status, text = "unregistered", ""
        by_status[status] += 1
        by_rule[f.rule] += 1
        items.append({"path": f.path, "line": f.line, "rule": f.rule, "qualname": f.qualname, "snippet": f.snippet,
                      "status": status, "text": text})
    dirty = _git("status", "--porcelain", "--", "backend", "src", "tests", "realtime_demo.py", "start_fullstack.ps1")
    return {
        "generated_by": {
            "command": command,
            "git_commit": _git("rev-parse", "HEAD").strip(),
            "code_dirty": bool(dirty.strip()),
            "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "note": REPORT_NOTE,
        "scope": scope,
        "rules": dict(RULE_DESCRIPTIONS),
        "findings": items,
        "summary": {"by_status": by_status, "by_rule": by_rule,
                    "n_serving_files": len(scope["serving_files"]), "n_main_files": len(scope["main_files"])},
    }


def write_report(out, argv):
    report = build_report(_command_line(argv))
    parent = os.path.dirname(os.path.abspath(out))
    os.makedirs(parent, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return report


# ----------------------------------------------------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------------------------------------------------
def _rules_of(findings):
    return [f.rule for f in findings]


class TestRuleSelfCheck(unittest.TestCase):
    """AC2 (each rule fires on in-memory samples) and AC3 (valid code gives no finding)."""

    POSITIVE = {
        "A-stdlib": [
            "import random\nx = random.random()\n",
            "import random as r\ndef pick(xs):\n    return r.choice(xs)\n",
            "from random import shuffle\nshuffle(xs)\n",
            "import random\nrandom.seed()\n",
            "import random\ndef a():\n    random.seed(1)\ndef b():\n    return random.random()\n",
        ],
        "A-numpy": [
            "import numpy as np\nx = np.random.rand(3)\n",
            "import numpy\nx = numpy.random.normal(0, 1)\n",
            "from numpy import random as npr\nx = npr.uniform()\n",
            "import numpy as np\nrng = np.random.default_rng()\n",
            "import numpy as np\nrng = np.random.default_rng(None)\n",
            "from numpy.random import randn\nx = randn(2)\n",
        ],
        "A-torch": [
            "import torch\nx = torch.rand(3)\n",
            "import torch\ny = torch.randn_like(x)\n",
            "import numpy as np\nimport torch\nrng = np.random.default_rng(int(torch.randint(0, 5, (1,))))\n",
            "import torch\nx.uniform_(0, 1)\n",
            "import torch\ng = torch.Generator()\n",
        ],
        "B-import": [
            "from unittest import mock\n",
            "import unittest.mock\n",
            "from unittest.mock import patch\n",
            "import mock\n",
        ],
        "B-name": [
            "m = MagicMock()\n",
            "AsyncMock()\n",
            "from unittest import mock\nmock.patch(\"a.b\")\n",
        ],
        "C-name": [
            "fake_result = 1\n",
            "def simulate_landmarks():\n    pass\n",
            "class SyntheticStream:\n    pass\n",
            "def f(placeholder_gloss):\n    pass\n",
            "for mock_frame in frames:\n    pass\n",
            "mockPredictor = 1\n",
            "dummies = []\n",
        ],
        "C-string": [
            "print(\"Using synthetic frames\")\n",
            "if src == \"mock\":\n    pass\n",
            "s = f\"dummy {x}\"\n",
            "msg = \"dữ liệu giả lập\"\n",
            "@app.get(\"/x\")\ndef h():\n    \"\"\"Returns simulated results.\"\"\"\n    return 1\n",
        ],
        "C-result": [
            "def f():\n    return {\"gloss\": \"xin chào\", \"confidence\": 0.9}\n",
            "self.last_gloss = \"cảm ơn\"\n",
            "confidence = 0.87\n",
            "out[\"translation\"] = \"Tôi đi học\"\n",
            "def predict(x):\n    return \"a\"\n",
            "r = {\"top5\": [(\"a\", 0.9)]}\n",
        ],
        "D-binding": [
            "latency_ms = 12.5\n",
            "ACCURACY = 0.751\n",
            "m = {\"top1\": 75.1}\n",
            "self.fps = 30\n",
            "stats[\"latency_ms\"] = 42\n",
            "wer = 100.0 if x else 0.0\n",
            "top5_acc: float = 0.9\n",
            "server_preprocess_ms = latency_ms * 0.4\n",
            "hud.draw(fps=30.0)\n",
            "def f(latency_ms=12.0):\n    pass\n",
            "m = {\"accuracy\": \"75.1\"}\n",
        ],
        "D-string": [
            "label = \"Độ chính xác 92%\"\n",
            "label = f\"Top-1: 75.1 ({n} clip)\"\n",
            "label = \"latency 35 ms\"\n",
            "label = \"~30 FPS\"\n",
            "label = \"accuracy=0.87\"\n",
            "print(\"WER 23.4\")\n",
            "@app.get(\"/m\")\ndef m():\n    \"\"\"Mô hình đạt 87% trên tập test.\"\"\"\n    return 1\n",
        ],
    }

    NEGATIVE = [
        "import numpy as np\nrng = np.random.default_rng(0)\nv = rng.normal()\n",
        "import numpy as np\nrng = np.random.default_rng(seed)\n",
        "import random\nv = random.Random(42).random()\n",
        "import numpy as np\ndef f():\n    np.random.seed(0)\n    return np.random.randn(2)\n",
        "import torch\ndef g():\n    torch.manual_seed(0)\n    return torch.rand(2)\n",
        "import torch\nx = torch.rand(2, generator=g)\n",
        "import torch\ng = torch.Generator()\ng.manual_seed(1)\n",
        "import torch\nimport torch.nn as nn\nnn.init.trunc_normal_(w, std=0.02)\n",
        "from torch.nn import init\ninit.normal_(w)\n",
        "self.random_scale(x)\n",
        "# np.random.rand()\nx = 1\n",
        "\"\"\"Synthetic dummy data, 87% accuracy, sub-10ms latency.\"\"\"\nx = 1\n",
        "def warm(x):\n    \"\"\"Run the model once on a dummy tensor.\"\"\"\n    return x\n",
        "infer_ms = 0.0\n",
        "best_top1 = -1.0\n",
        "latency_ms = (t1 - t0) * 1000.0\n",
        "fps = 1.0 / dt\n",
        "import numpy as np\nfps = float(np.mean(t)) if t else 0.0\n",
        "m = {\"top1\": round(top1, 2)}\n",
        "v = prediction.get(\"latency_ms\", 0.0)\n",
        "label = f\"{fps:.1f} FPS | {lat:.1f}ms\"\n",
        "fmt = \"%.2f\"\n",
        "fmt = \"%d%%\"\n",
        "label = \"Top-5 Dự đoán:\"\n",
        "label = \"precision, recall, f1-score\"\n",
        "r = {\"gloss\": \"...\", \"confidence\": 0.0, \"prediction\": None, \"top5\": [], \"translation\": \"\"}\n",
        "r = {\"gloss\": pred[\"gloss\"]}\n",
        "confidence_threshold = 0.45\n",
        "def f(min_detection_confidence: float = 0.5):\n    pass\n",
        "h = Holistic(min_detection_confidence=0.5)\n",
        "WS_MAX_MESSAGE_BYTES = 1_048_576\n",
        "ALPHABET_MAX_ABS_COORD = 10.0\n",
        "import unittest\n",
        "def patch_image(x):\n    pass\n",
        "label = \"giải mã CTC\"\n",
        "sample_id = 3\n",
    ]

    def test_each_rule_fires(self):
        self.assertEqual(set(self.POSITIVE), set(RULES))
        self.assertEqual(len(RULES), 10)
        for rule, samples in self.POSITIVE.items():
            for i, sample in enumerate(samples):
                with self.subTest(rule=rule, sample=i):
                    found = scan_source(sample, "mem/x.py", ALL_RULES)
                    self.assertIn(rule, _rules_of(found), f"{rule} not reported for:\n{sample}\n-> {found}")

    def test_valid_code_is_silent(self):
        for i, sample in enumerate(self.NEGATIVE):
            with self.subTest(sample=i):
                self.assertEqual(scan_source(sample, "mem/x.py", ALL_RULES), [], sample)

    def test_seed_in_other_function_does_not_count(self):
        src = "import random\ndef a():\n    random.seed(1)\ndef b():\n    return random.random()\n"
        found = scan_source(src, "mem/x.py", ALL_RULES)
        self.assertEqual([(f.rule, f.qualname, f.line) for f in found], [("A-stdlib", "b", 5)])

    def test_rng_inside_seed_argument(self):
        src = "import numpy as np\nimport torch\nrng = np.random.default_rng(int(torch.randint(0, 5, (1,))))\n"
        rules = _rules_of(scan_source(src, "mem/x.py", ALL_RULES))
        self.assertIn("A-torch", rules)
        self.assertNotIn("A-numpy", rules)

    def test_result_dict_counts_each_pair(self):
        src = "def f():\n    return {\"gloss\": \"xin chào\", \"confidence\": 0.9}\n"
        self.assertEqual(_rules_of(scan_source(src, "mem/x.py", ALL_RULES)).count("C-result"), 2)

    def test_each_string_unit_counts(self):
        found = scan_source("a = \"mock\"\nb = \"mock\"\n", "mem/x.py", ALL_RULES)
        self.assertEqual([(f.rule, f.line) for f in found], [("C-string", 1), ("C-string", 2)])

    def test_adjacent_fstrings_are_one_unit(self):
        src = "x = 1\nmsg = (f\"acc {a} \"\n       f\"= 75.1% on \"\n       f\"{n} clips\")\n"
        found = [f for f in scan_source(src, "mem/x.py", ALL_RULES) if f.rule == "D-string"]
        self.assertEqual([(f.line, f.qualname) for f in found], [(2, "<module>")])

    def test_line_of_multiline_sample(self):
        src = "import torch\n\n\nclass A:\n    def f(self, x):\n        y = x + 1\n        z = torch.rand(3)\n        return y\n"
        found = scan_source(src, "mem/x.py", ALL_RULES)
        self.assertEqual([(f.rule, f.line, f.qualname, f.snippet) for f in found],
                         [("A-torch", 7, "A.f", "z = torch.rand(3)")])

    def test_rules_argument_restricts_output(self):
        src = "import random\nfake_x = random.random()\nlatency_ms = 12.5\n"
        self.assertEqual(sorted(_rules_of(scan_source(src, "mem/x.py", MAIN_RULES))), ["D-binding"])
        self.assertEqual(sorted(_rules_of(scan_source(src, "mem/x.py", ALL_RULES))),
                         ["A-stdlib", "C-name", "D-binding"])

    def test_syntax_error_propagates(self):
        with self.assertRaises(SyntaxError):
            scan_source("def (:\n", "mem/x.py", ALL_RULES)

    def test_finding_shape(self):
        long_line = "label = \"mock " + "x" * 300 + "\"\n"
        (f,) = scan_source(long_line, "mem/x.py", ALL_RULES)
        self.assertEqual((f.path, f.line, f.rule, f.qualname), ("mem/x.py", 1, "C-string", "<module>"))
        self.assertLessEqual(len(f.snippet), 160)


class TestScope(unittest.TestCase):
    """AC4: import closure (temp repo + real tree), MAIN parses, scripts scope."""

    def setUp(self):
        self.tmp = None

    def tearDown(self):
        if self.tmp:
            shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_resolver_on_temp_repo(self):
        self.tmp = tempfile.mkdtemp(prefix="plan10_scope_")
        self.assertFalse(os.path.abspath(self.tmp).startswith(PROJECT_ROOT + os.sep))
        files = {
            "entry.py": "import pkg.a\nimport json\nimport tool\n\ndef f():\n    from pkg import b\n    return b\n",
            "pkg/__init__.py": "",
            "pkg/a.py": "from .c import d\n",
            "pkg/b.py": "X = 1\n",
            "pkg/c.py": "d = 1\n",
            "pkg/unused.py": "Y = 2\n",
            "scripts/tool.py": "Z = 3\n",
        }
        for rel, text in files.items():
            path = os.path.join(self.tmp, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        self.assertEqual(set(serving_closure(self.tmp, ("entry.py",))),
                         {"entry.py", "pkg/__init__.py", "pkg/a.py", "pkg/b.py", "pkg/c.py", "scripts/tool.py"})

    def test_b_real_tree_serving(self):
        _, scope = _cached_scan()
        serving, main = set(scope["serving_files"]), set(scope["main_files"])
        self.assertFalse(set(MIN_SERVING) - serving, "MIN_SERVING missing -> CẦN PLANNER")
        self.assertEqual(serving & set(NOT_SERVING), set())
        self.assertLessEqual(serving, main)
        on_disk = {_rel(PROJECT_ROOT, p) for top in ("backend", "src")
                   for p in glob.glob(os.path.join(PROJECT_ROOT, top, "**", "*.py"), recursive=True)}
        on_disk = {p for p in on_disk if "__pycache__" not in p.split("/")}
        self.assertTrue(on_disk)
        self.assertLessEqual(on_disk, main)
        print(f"\n[scope] serving={len(serving)} main={len(main)}")

    def test_c_main_files_parse(self):
        _, scope = _cached_scan()
        for rel in scope["main_files"]:
            with self.subTest(rel):
                ast.parse(_read(os.path.join(PROJECT_ROOT, rel)), filename=rel)

    def test_d_scripts_scope(self):
        _, scope = _cached_scan()
        self.assertIn(UVICORN_TARGET, _read(os.path.join(PROJECT_ROOT, "start_fullstack.ps1")))
        self.assertEqual(set(scope["scripts_realtime"]), set(SCRIPTS_REALTIME),
                         "phạm vi scripts đổi — CẦN PLANNER")
        self.assertEqual(set(SCRIPTS_REALTIME), set())


class TestBackendSourceGuard(unittest.TestCase):
    """AC5: the real tree matches the registries exactly."""

    def test_a_tree_matches_registry(self):
        findings, _ = _cached_scan()
        cmp = compare_registry(findings, ALLOWED, KNOWN_VIOLATIONS)
        self.assertEqual((cmp["unregistered"], cmp["changed"], cmp["stale"]), ([], [], []),
                         "\n" + format_comparison(cmp))

    def test_b_registry_shape(self):
        self.assertEqual(len(PLAN10_APPROVED_ALLOWED), 16)
        self.assertLessEqual(set(ALLOWED), PLAN10_APPROVED_ALLOWED)
        self.assertEqual(set(ALLOWED) & set(KNOWN_VIOLATIONS), set())
        for reg in (ALLOWED, KNOWN_VIOLATIONS):
            for key, (count, text) in reg.items():
                with self.subTest(key=key):
                    self.assertEqual(len(key), 3)
                    self.assertIn(key[1], ALL_RULES)
                    self.assertIsInstance(count, int)
                    self.assertGreaterEqual(count, 1)
                    self.assertTrue(isinstance(text, str) and text.strip())

    def test_c_summary_line(self):
        known, allowed = registry_totals()
        print(f"\n[DoD7-guard] known={known} allowed={allowed}")


class TestRegistryComparator(unittest.TestCase):
    """AC6: mutations on the real registry (backend/main.py is read from disk and changed in memory only)."""

    TARGET = "backend/main.py"
    MUTATIONS = [
        ("import random\n_v = random.random()\n", ("A-stdlib",)),
        ("from unittest.mock import MagicMock\n", ("B-import",)),
        ("_r = {\"gloss\": \"xin chào\", \"confidence\": 0.9}\n", ("C-result",)),
        ("_fake_latency_ms = 12.5\n", ("C-name", "D-binding")),
        ("def _h():\n    return \"Độ chính xác 92%\"\n", ("D-string",)),
    ]

    @classmethod
    def setUpClass(cls):
        cls.findings, cls.scope = _cached_scan()

    def _sha(self):
        with open(os.path.join(PROJECT_ROOT, self.TARGET), "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    def _registered_key(self):
        reg = KNOWN_VIOLATIONS or ALLOWED
        self.assertTrue(reg, "both registries are empty")
        return sorted(reg)[0], reg[sorted(reg)[0]][0]

    def test_a_mutations_are_reported(self):
        sha_before = self._sha()
        self.assertIn(self.TARGET, self.scope["serving_files"])
        rules = rules_for(self.TARGET, self.scope["serving_files"])
        self.assertEqual(rules, ALL_RULES)
        text = _read(os.path.join(PROJECT_ROOT, self.TARGET))
        others = [f for f in self.findings if f.path != self.TARGET]
        for mutation, expected in self.MUTATIONS:
            mutated = scan_source(text + "\n" + mutation, self.TARGET, rules)
            cmp = compare_registry(others + mutated, ALLOWED, KNOWN_VIOLATIONS)
            for rule in expected:
                with self.subTest(mutation=mutation, rule=rule):
                    self.assertTrue(any(f.rule == rule and f.path == self.TARGET for f in cmp["unregistered"]),
                                    format_comparison(cmp))
        self.assertEqual(self._sha(), sha_before)

    def test_b_duplicate_is_changed(self):
        key, count = self._registered_key()
        dup = next(f for f in self.findings if finding_key(f) == key)
        cmp = compare_registry(self.findings + [dup], ALLOWED, KNOWN_VIOLATIONS)
        self.assertIn((key, count, count + 1), cmp["changed"])
        self.assertEqual(cmp["unregistered"], [])

    def test_c_removed_is_stale(self):
        key, count = self._registered_key()
        cmp = compare_registry([f for f in self.findings if finding_key(f) != key], ALLOWED, KNOWN_VIOLATIONS)
        self.assertIn((key, count), cmp["stale"])

    def test_d_intact_is_clean(self):
        cmp = compare_registry(self.findings, ALLOWED, KNOWN_VIOLATIONS)
        self.assertEqual((cmp["unregistered"], cmp["changed"], cmp["stale"]), ([], [], []),
                         "\n" + format_comparison(cmp))


class TestImportLight(unittest.TestCase):
    """AC7-a: importing the guard pulls no heavy / project runtime module."""

    def test_no_heavy_import(self):
        code = ("import sys, tests.test_backend_source_guard; print(sorted(m for m in "
                "('torch','numpy','cv2','mediapipe','fastapi','backend.main') if m in sys.modules))")
        out = subprocess.run([sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True,
                             timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "[]")


class TestReportMode(unittest.TestCase):
    """§3.7 / AC7-c: two report runs give the same findings and summary; no absolute path in the body."""

    def test_report_is_deterministic(self):
        tmp = tempfile.mkdtemp(prefix="plan10_report_")
        try:
            bodies = []
            for i in range(2):
                out = os.path.join(tmp, f"r{i}.json")
                run = subprocess.run([sys.executable, "-m", "tests.test_backend_source_guard", "--report", out],
                                     cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120)
                self.assertEqual(run.returncode, 0, run.stderr)
                with open(out, encoding="utf-8") as fh:
                    rep = json.load(fh)
                gen = rep.pop("generated_by")
                self.assertRegex(gen["git_commit"], r"^[0-9a-f]{40}$")
                self.assertIsInstance(gen["code_dirty"], bool)
                self.assertIn("--report", gen["command"])
                body = json.dumps(rep, ensure_ascii=False)
                self.assertNotIn(PROJECT_ROOT, body)
                self.assertNotIn(PROJECT_ROOT.replace(os.sep, "/"), body)
                bodies.append(rep)
            self.assertEqual(bodies[0]["findings"], bodies[1]["findings"])
            self.assertEqual(bodies[0]["summary"], bodies[1]["summary"])
            self.assertEqual(bodies[0], bodies[1])
            self.assertEqual(set(bodies[0]["rules"]), set(RULES))
            self.assertEqual(bodies[0]["note"], REPORT_NOTE)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if "--report" in sys.argv[1:]:
        _argv = sys.argv[1:]
        _i = _argv.index("--report")
        if _i + 1 >= len(_argv):
            sys.exit("usage: python -m tests.test_backend_source_guard --report <out.json>")
        _rep = write_report(_argv[_i + 1], _argv)
        print(f"[DoD7-guard] report {_argv[_i + 1]}: by_status={json.dumps(_rep['summary']['by_status'])} "
              f"by_rule={json.dumps(_rep['summary']['by_rule'])}")
        sys.exit(0)
    unittest.main()
