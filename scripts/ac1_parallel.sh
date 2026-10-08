#!/usr/bin/env bash
# Chạy các module unittest SONG SONG (mỗi module một tiến trình riêng) và in tóm tắt từng module.
# Dùng:  scripts/ac1_parallel.sh [-j N] tests.test_a tests.test_b ...      (mặc định -j 4)
# Vì sao: AC-1 tuần tự ~14 phút, 3 module chiếm ~95% (test_level1_segmenter ~350s, test_hand_live_equivalence ~270s,
#         test_level1_equivalence ~195s khi chạy riêng) ⇒ song song còn ~6 phút.
#         Tập module đỏ trùng mốc tuần tự (đối chiếu 8/10, 27/28 module). Chỉ tăng tốc; tiêu chí chấp nhận không đổi.
# Log từng module: _work/ac1_parallel/<module>.log. Mã thoát: 0 nếu mọi module OK, 1 nếu có module FAIL/ERROR.
set -u
cd "$(dirname "$0")/.." || exit 2
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1 MSYS_NO_PATHCONV=1
PY=".venv/Scripts/python.exe"; [ -x "$PY" ] || PY="python"
J=4
[ "${1:-}" = "-j" ] && { J="$2"; shift 2; }
[ $# -gt 0 ] || { echo "Cần ít nhất một module, ví dụ: tests.test_level1_core" >&2; exit 2; }

OUT="_work/ac1_parallel"; mkdir -p "$OUT"; rm -f "$OUT"/*.log "$OUT/summary.txt"
export PY OUT
printf '%s\n' "$@" | xargs -P "$J" -I{} bash -c '
  s=$(date +%s); "$PY" -m unittest "$1" >"$OUT/$1.log" 2>&1; rc=$?
  echo "$(( $(date +%s) - s ))s rc=$rc $1 $(grep -aE "^Ran " "$OUT/$1.log" | head -1) $(grep -aE "^(OK|FAILED)" "$OUT/$1.log" | tail -1)" >>"$OUT/summary.txt"
' _ {}
sort -t= -k2 "$OUT/summary.txt"
BAD=$(grep -c "rc=[1-9]" "$OUT/summary.txt")
echo "[ac1_parallel] $# module, lỗi: $BAD (log ở $OUT/)"
[ "$BAD" -eq 0 ]
