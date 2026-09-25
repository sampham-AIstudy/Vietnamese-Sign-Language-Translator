---
name: vsl-cloud-jobs
description: Chạy việc nặng (trích landmark, train, đánh giá) của dự án VSL trên Kaggle kernel hoặc Colab thay vì máy local. Dùng khi cần push/theo dõi kernel Kaggle, dùng Colab MCP, cài mediapipe đúng phiên bản trên cloud, hoặc lấy output về.
---

# VSL cloud jobs (Kaggle + Colab)

Nguyên tắc: máy local chỉ chạy smoke test vài giây; mọi thứ nặng chạy cloud. Chỉ cài trong `.venv` (local).
Kaggle CLI: `.venv/Scripts/kaggle` (OAuth, user `phmvnsm33`). Không đọc/in `~/.kaggle/*`.

## Kaggle kernel (batch, chạy nền, 4 CPU, T4 ~30 h/tuần)
- Mỗi job = thư mục `kaggle/<kernel>/` gồm `kernel-metadata.json` + 1 file `.py` (`kernel_type: script`).
  Luôn `is_private: true`. Cần pip/git → `enable_internet: true`.
- Code lấy bằng `git clone --depth 1 -b fix/audit-round2 https://github.com/sampham-AIstudy/Vietnamese-Sign-Language-Translator.git /tmp/vslt`
  → **commit + push trước khi push kernel**. Clone/dữ liệu trung gian để ở `/tmp`; chỉ ghi kết quả vào `/kaggle/working` (bị tải về làm output).
- Input: `dataset_sources` (vd `aresusayhi/vsl-vietnamese-sign-languages` = QIPEDC, `hauuto/vietnamese-sign-language-alphabet`) hoặc
  `kernel_sources` (output kernel trước). Tìm đường dẫn bằng `glob("/kaggle/input/**/<file>", recursive=True)` — mount path thay đổi.
- Push: `cd kaggle/<kernel> && kaggle kernels push -p .` (thêm `--accelerator NvidiaTeslaT4` cho GPU).
  **Bẫy CLI 2.2.4**: `-p kaggle/<dir>` với đường dẫn nhiều cấp có thể hỏng mà vẫn exit 0 → luôn `cd` vào rồi `-p .`.
- Theo dõi: `kaggle kernels status phmvnsm33/<kernel>`; log chỉ có khi xong: `kaggle kernels logs ...`;
  output: `kaggle kernels output phmvnsm33/<kernel> -p <dir>`. Đợi bằng vòng lặp nền (`run_in_background`), không poll dày.
- Dataset upload: `kaggle datasets create -p .` (mặc định private; **không** `--public`). Mạng local ~100 KB/s → tránh upload lớn;
  ưu tiên để cloud tự tải (GitHub, dataset công khai trên Kaggle, `kagglehub` tải public dataset không cần login).

## MediaPipe đúng phiên bản trên cloud
Backend dùng **mediapipe 0.10.14** (`mp.solutions.holistic/hands`). Kaggle/Colab mới chạy Python 3.13 → chỉ có mediapipe ≥1.0 (bỏ `solutions`).
Luôn tạo env riêng:
```
pip install -q uv && uv venv -q /tmp/mp311 --python 3.11
uv pip install -q --python /tmp/mp311/bin/python mediapipe==0.10.14 'numpy<2' opencv-python-headless==4.10.0.84
MPLBACKEND=Agg /tmp/mp311/bin/python scripts/...    # Colab kernel đặt MPLBACKEND inline → matplotlib py3.11 lỗi
```
Train (torch) chạy bằng Python mặc định của kernel; chỉ bước trích landmark cần env 3.11.

## Colab qua MCP (tương tác, 2 CPU, T4 khi chủ dự án bật)
- Gọi `mcp__colab-mcp__open_colab_browser_connection` trước → mở khoá add/update/run cell. Tab Colab phải đang mở.
- Kiểm tra GPU: `torch.cuda.is_available()`; không có dòng "GPU RAM" trên Colab = runtime CPU (không có `nvidia-smi`).
- MCP server là `.venv/uv-tools/bin/colab-mcp.exe` (cài ghim commit, không cần mạng lúc khởi động). Nếu timeout: `/mcp` → reconnect.

## Kernel hiện có
| Kernel | Việc |
|---|---|
| `vsl-extract-qipedc` | Holistic 67 khớp cho 4362 video QIPEDC → `qipedc_kps/` |
| `vsl-extract-alphabet` | Hands cho hauuto + chữ cái QIPEDC → `alphabet_hands/` |
| `vsl-train-unified` | STGCN 876 lớp (GPU), input = output `vsl-extract-qipedc` |
| `vsl-train-alphabet` | Cấp 1 LOSO (CPU), input = output `vsl-extract-alphabet` |
