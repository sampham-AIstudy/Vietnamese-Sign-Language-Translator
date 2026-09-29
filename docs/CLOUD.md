# VSLT trên Claude Code on the web (cloud)

Đọc file này khi `CLAUDE_CODE_REMOTE=true`. Mọi quy tắc khác giữ nguyên: CLAUDE.md, docs/STATE.md,
docs/prompts/orchestrator.md + hai phụ lục, docs/prompts/autopilot.md.

## 1. Cấu hình environment (người dùng làm trên claude.ai/code)
- **Network access: Custom**, tick "Also include default list", thêm:
  `download.pytorch.org`, `www.kaggle.com`, `api.kaggle.com`, `storage.googleapis.com`
  (mặc định "Trusted" KHÔNG tới được Kaggle và download.pytorch.org).
- **Setup script:** dán nguyên nội dung `scripts/cloud_setup.sh` (tạo venv ngoài repo `/opt/vslt-venv`, mediapipe 0.10.14,
  torch CPU). Script chạy bằng root, trước khi Claude Code khởi động, được cache ~7 ngày.
- **Environment variables** (dạng `.env`, KHÔNG bí mật — ai dùng environment này đều đọc được; không có trong setup script):
  ```
  KAGGLE_USERNAME=phmvnsm33
  KAGGLE_KEY=<API key Kaggle của bạn>
  PYTHONIOENCODING=utf-8
  VSL_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
  ```
  Không ghi token vào repo, không in token ra log.

## 2. Việc đầu phiên (agent cloud tự làm, mỗi phiên)
```bash
cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || true
[ -e .venv ] || ln -s /opt/vslt-venv .venv          # đường dẫn Python trên cloud: .venv/bin/python (local Windows: .venv/Scripts/python)
(cd frontend && npm ci --no-audit --no-fund)       # node 22 có sẵn; dự án đã chạy local với node 25
.venv/bin/kaggle datasets list --mine | head -3    # kiểm credential (cần network Custom như mục 1)
```
Không có `vslt_usage.json` trên cloud → theo usage_guard_addendum: hạn mức "KHÔNG BIẾT" → chỉ giao đơn vị việc nhỏ nhất,
ghi STATE.md + commit sau mỗi đơn vị.

## 3. Dữ liệu (bị gitignore — clone trên cloud KHÔNG có)
Nhiều test skip nếu thiếu dữ liệu cục bộ (11 file test có skipUnless). Yêu cầu "0 skip" chỉ đạt sau khi khôi phục dữ liệu:
- Checkpoint + logits bước 4, checkpoint Cấp 1, bằng chứng provenance: 2 dataset PRIVATE
  `phmvnsm33/vslt-step4-artifacts` và `phmvnsm33/vslt-provenance-artifacts`. Khôi phục bằng lệnh ở README mục
  "Artifact không nằm trong git" (scripts/archive_private_kaggle.py restore), dùng `.venv/bin/python`.
- Keypoint QIPEDC (native + 360 px): output kernel Kaggle `phmvnsm33/vsl-pack-qipedc`, `vsl-extract-qipedc`,
  `vsl-extract-qipedc360-s{0,1,2}` (`kaggle kernels output ... -p <thư mục tạm>` rồi đặt vào data/processed/ theo docs/data_registry.md).
- Video gốc: QIPEDC (dataset `aresusayhi/vsl-vietnamese-sign-languages`), hauuto (dataset `hauuto/vietnamese-sign-language-alphabet`,
  GIẤY PHÉP CHƯA RÕ — chỉ dùng nội bộ, không commit video/landmark/frame).
- Không có dữ liệu cần thiết → ghi rõ test nào skip và vì sao; KHÔNG coi skip là pass; báo người dùng.

## 4. Khác biệt với máy local
- Không có GPU; train nặng vẫn chỉ trên Kaggle (kernel private) như cũ.
- `start_fullstack.ps1` là PowerShell và e2e kế hoạch 06 (B8) dùng Edge + puppeteer-core: trên cloud có thể không có pwsh/Edge.
  Nếu B8 không chạy được trên cloud → "CẦN PLANNER"/báo người dùng, không đổi tiêu chí tại chỗ.
- Landmark trích trên Linux có thể lệch nhẹ so với Windows (xem reports/fingerspell_live_2026-09-29/hand_live_check.json):
  test tương đương so hai đường TRÊN CÙNG máy thì vẫn phải bằng hệt.
- Nhánh: làm tiếp trên `feat/vslt-complete`; không push lên main.
