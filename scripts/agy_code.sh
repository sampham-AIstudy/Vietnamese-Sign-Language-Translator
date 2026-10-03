#!/usr/bin/env bash
# Cầu nối Claude -> Antigravity CLI (agy): giao MỘT kế hoạch/chặng cho agy triển khai (vai Coder), CÓ rào chắn + cổng hạn mức.
#
# Dùng:  scripts/agy_code.sh <docs/plans/NN-ten.md> [--steps "1-3"] [--review docs/reviews/NN-review.md]
#                            [--model gemini|opus|sonnet|auto|<id>] [--effort low|medium|high|xhigh|max]
#                            [--units N] [--timeout GIÂY] [--dry-run]
#   --model: họ model (tự lấy BẢN MỚI NHẤT trong `agy models`) hoặc id đầy đủ. Mặc định gemini (env AGY_MODEL).
#   --effort: mặc định high (env AGY_EFFORT). Cổng hạn mức có thể HẠ effort / đổi họ nếu hạn mức không đủ.
#   --units: số bước kế hoạch giao lần này (mặc định suy ra từ --steps; không có --steps thì coi là 3).
#   --dry-run: chỉ chụp snapshot + chọn model + in kết quả cổng, KHÔNG chạy agy.
# Trình tự: snapshot guard -> cổng hạn mức (chọn model/effort) -> agy (git hook chặn commit sai) -> ghi sổ usage -> kiểm tra guard.
# Mã thoát: 0=DONE, 10=CẦN PLANNER, 11=BỊ CHẶN, 12=agy không in STATUS, 13=hết giờ, 14=agy chạm giới hạn hạn mức giữa chừng,
#           20=KHÔNG ĐỦ hạn mức (chưa chạy), 21=GUARD phát hiện vi phạm, 2=sai tham số, 3=thiếu agy
# Log đầy đủ: _work/agy_logs/<giờ>-<kế hoạch>.log
set -u
cd "$(dirname "$0")/.." || exit 2
export MSYS_NO_PATHCONV=1 PYTHONUTF8=1 PYTHONIOENCODING=utf-8

PY=".venv/Scripts/python.exe"; [ -x "$PY" ] || PY="python"
PLAN="" ; STEPS="" ; REVIEW="" ; UNITS="" ; DRY=0
MODEL="${AGY_MODEL:-gemini}"
EFFORT="${AGY_EFFORT:-high}"
TMO="${AGY_TIMEOUT:-2400}"

while [ $# -gt 0 ]; do
  case "$1" in
    --steps)   STEPS="$2"; shift 2 ;;
    --review)  REVIEW="$2"; shift 2 ;;
    --model)   MODEL="$2"; shift 2 ;;
    --effort)  EFFORT="$2"; shift 2 ;;
    --units)   UNITS="$2"; shift 2 ;;
    --timeout) TMO="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -*)        echo "Tham số lạ: $1" >&2; exit 2 ;;
    *)         PLAN="$1"; shift ;;
  esac
done

[ -n "$PLAN" ] && [ -f "$PLAN" ] || { echo "Thiếu/không thấy file kế hoạch: '$PLAN'" >&2; exit 2; }
[ -z "$REVIEW" ] || [ -f "$REVIEW" ] || { echo "Không thấy file review: '$REVIEW'" >&2; exit 2; }
command -v agy >/dev/null 2>&1 || { echo "Không tìm thấy 'agy' trong PATH" >&2; exit 3; }

if [ -z "$UNITS" ]; then
  UNITS="$("$PY" - "$STEPS" <<'EOF'
import re, sys
s = sys.argv[1].strip()
if not s:
    print(3); sys.exit()          # không có --steps: coi là 3 bước (giả định, thận trọng)
if len(s) > 40:
    print(1); sys.exit()          # mô tả tự do (không phải danh sách mã bước) -> coi là 1 bước
n = 0
for t in re.split(r"[,\s]+", s):
    m = re.fullmatch(r"(\d+)-(\d+)", t)
    if m:
        n += int(m.group(2)) - int(m.group(1)) + 1
    elif t:
        n += 1                    # mã bước như T1, A1, B5, 3
print(max(n, 1))
EOF
)"
fi

mkdir -p _work/agy_logs
LOG="_work/agy_logs/$(date +%Y%m%d-%H%M%S)-$(basename "$PLAN" .md).log"
GDIR="_work/agy_guard"

# 1) Snapshot: file/thư mục chưa commit của NGƯỜI DÙNG được bảo vệ + phạm vi (khối ```scope) của kế hoạch
"$PY" scripts/agy_guard.py snapshot "$PLAN" "$GDIR" | tee "$LOG"

# 2) Cổng hạn mức: chọn model/effort vừa ngân sách (không bao giờ cố tình chạm giới hạn)
CHOICE="$("$PY" scripts/agy_usage.py choose "$MODEL" "$EFFORT" "$UNITS" --plan "$PLAN")"; CRC=$?
echo "[agy_code] cổng hạn mức: $CHOICE" | tee -a "$LOG"
[ "$CRC" -eq 20 ] && { echo "[agy_code] KHÔNG ĐỦ hạn mức agy — không chạy. Chia nhỏ --steps hoặc chờ reset."; exit 20; }
SEL_MODEL="$(echo "$CHOICE" | sed -n 's/.*MODEL=\([^ ]*\).*/\1/p')"
SEL_EFFORT="$(echo "$CHOICE" | sed -n 's/.*EFFORT=\([^ ]*\).*/\1/p')"
[ -n "$SEL_MODEL" ] || { echo "[agy_code] không chọn được model: $CHOICE" >&2; exit 20; }
[ "$DRY" -eq 1 ] && { echo "[agy_code] dry-run xong (không chạy agy). units=${UNITS}"; exit 0; }

PROMPT="Bạn là CODER của dự án VSLT. Đọc và tuân thủ docs/prompts/agy_coder.md và AGENTS.md trước khi làm gì khác. Kế hoạch được giao: ${PLAN}."
[ -z "$STEPS" ]  || PROMPT="${PROMPT} CHỈ làm các bước: ${STEPS} (không làm bước khác)."
[ -z "$REVIEW" ] || PROMPT="${PROMPT} Đây là lần SỬA LẠI: đọc ${REVIEW} và sửa đúng các mục CHANGES_REQUESTED."
PROMPT="${PROMPT} Một git hook sẽ CHẶN commit sai phạm vi/đụng file của người dùng/làm yếu test; nếu bị chặn hãy dừng và báo, đừng lách (--no-verify bị phát hiện). Kết thúc bằng báo cáo đúng định dạng trong agy_coder.md, dòng cuối là STATUS: DONE | CẦN PLANNER | BỊ CHẶN."

echo "[agy_code] plan=${PLAN} steps=${STEPS:-all} units=${UNITS} model=${SEL_MODEL} effort=${SEL_EFFORT:-(theo hậu tố)} timeout=${TMO}s" | tee -a "$LOG"

# 3) Chạy agy. Hook được tiêm bằng biến môi trường cho riêng tiến trình này (không đổi cấu hình git của repo).
EFF_ARGS=(); [ -z "$SEL_EFFORT" ] || EFF_ARGS=(--effort "$SEL_EFFORT")
HOOKS="$(pwd -W 2>/dev/null || pwd)/scripts/githooks"
(
  export AGY_GUARD=1 AGY_GUARD_DIR="$GDIR" AGY_PY="$PWD/$PY"
  export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0="$HOOKS"
  timeout "$TMO" agy -p "$PROMPT" --mode accept-edits --model "$SEL_MODEL" "${EFF_ARGS[@]}" >>"$LOG" 2>&1
)
RC=$?

# 4) Phát hiện chạm hạn mức giữa chừng + ghi sổ đo usage thật
QUOTA=0
grep -qiE "credits balance is too low|quota (is )?(exhausted|exceeded)|RESOURCE_EXHAUSTED|rate.?limit exceeded|daily (quota|limit)" "$LOG" && QUOTA=1
NOTE=""; [ "$QUOTA" -eq 1 ] && NOTE="limit_hit"; [ "$RC" -eq 124 ] && NOTE="${NOTE:+$NOTE,}timeout"
"$PY" scripts/agy_usage.py record "$UNITS" ${NOTE:+--note "$NOTE"} | tee -a "$LOG"

# 5) Guard sau chạy (bắt cả --no-verify, file của người dùng bị sửa, thay đổi ngoài phạm vi)
GRC=0
"$PY" scripts/agy_guard.py range "$GDIR"    2>&1 | tee -a "$LOG"; [ "${PIPESTATUS[0]}" -eq 0 ] || GRC=1
"$PY" scripts/agy_guard.py worktree "$GDIR" 2>&1 | tee -a "$LOG"; [ "${PIPESTATUS[0]}" -eq 0 ] || GRC=1

tail -n 40 "$LOG"
echo "[agy_code] agy exit=${RC}. Log đầy đủ: ${LOG}"
[ "$GRC" -ne 0 ] && { echo "[agy_code] GUARD PHÁT HIỆN VI PHẠM — xem các dòng BLOCK ở trên; KHÔNG chuyển sang review."; exit 21; }
[ "$RC" -eq 124 ] && { echo "[agy_code] HẾT GIỜ sau ${TMO}s — kiểm tra commit WIP và docs/plans/*-progress.md."; exit 13; }
if [ "$QUOTA" -eq 1 ]; then
  echo "[agy_code] agy CHẠM GIỚI HẠN hạn mức giữa chừng. Lưu trạng thái, không chạy lại ngay:"; "$PY" scripts/agy_usage.py status; exit 14
fi

STATUS_LINE="$(grep -E '^\s*\**STATUS:' "$LOG" | tail -n 1)"
case "$STATUS_LINE" in
  *DONE*)            exit 0 ;;
  *"CẦN PLANNER"*)   exit 10 ;;
  *"BỊ CHẶN"*)       exit 11 ;;
  *)                 echo "[agy_code] Không thấy dòng STATUS — coi như CHƯA XONG, phải đối chiếu git."; exit 12 ;;
esac
