# Huấn luyện trên Cloud (Kaggle / Colab)

Mọi việc nặng (trích landmark, train, đánh giá) chạy trên cloud; máy local chỉ chạy smoke test.
Quy trình chi tiết, bẫy thường gặp và lệnh: skill `.claude/skills/vsl-cloud-jobs/SKILL.md`.
Yêu cầu nhất quán train ↔ camera: skill `.claude/skills/vsl-landmark-consistency/SKILL.md`.

## Pipeline hiện hành (thư mục `kaggle/`)

| Kernel | Đầu vào | Việc | Đầu ra |
|---|---|---|---|
| `vsl-extract-qipedc` | Kaggle `aresusayhi/vsl-vietnamese-sign-languages` (QIPEDC) | `scripts/extract_keypoints_batch.py` — Holistic 67 khớp, mediapipe 0.10.14 | `qipedc_kps/*.npz` |
| `vsl-train-unified` (GPU T4 x2) | output `vsl-extract-qipedc` + VSL-GH upstream @ `6c351e6` | `prepare_canonical_vsl_gh.py` → `export_vslgh_segments.py` → `train_unified.py`, seed 42 trên GPU 0 và seed 43 trên GPU 1 song song | `run/` (seed 42, kết quả chính) + `run_seed43/` (chỉ đo dao động) |
| `vsl-extract-alphabet` | Kaggle `hauuto/vietnamese-sign-language-alphabet` + QIPEDC | `build_alphabet_tasks.py` → `extract_hands_batch.py` (MediaPipe Hands) | `alphabet_hands/*.npz` |
| `vsl-train-alphabet` (CPU) | output `vsl-extract-alphabet` | `train_alphabet_real.py` — LOSO 4 người + test ngoài QIPEDC | `alphabet_real_best.pt`, `alphabet_report.json` |

Chạy một kernel (code được clone từ branch trên GitHub, nên **commit + push trước**):
```powershell
cd kaggle\vsl-train-unified
..\..\.venv\Scripts\kaggle.exe kernels push -p . --accelerator NvidiaTeslaT4
..\..\.venv\Scripts\kaggle.exe kernels status phmvnsm33/vsl-train-unified
..\..\.venv\Scripts\kaggle.exe kernels output phmvnsm33/vsl-train-unified -p ..\..\reports\<run_dir>
```

## Phân bổ quota Kaggle (mỗi tuần: GPU T4 x2 30 h, TPU v5e-8 20 h; CPU không tính quota)
- **CPU**: trích landmark (MediaPipe chỉ chạy CPU), train Cấp 1. Không bật accelerator cho các kernel này.
- **GPU T4 x2**: train Cấp 2; mỗi phiên dùng cả 2 GPU (2 seed song song). Fine-tune ViT5 Cấp 3 nếu cần.
  Seed chính khai báo trước (42); các seed khác chỉ để báo độ dao động, không chọn seed theo kết quả test.
- **TPU v5e-8**: để dự phòng. Code STGCN/BiGRU là PyTorch + CUDA autocast, chuỗi dài thay đổi → chuyển sang
  torch_xla tốn công, lợi ích nhỏ với model nhỏ. Chỉ cân nhắc cho fine-tune ViT5 (T5 chạy tốt trên TPU với JAX).

## Dữ liệu và cách chia
- Manifest hợp nhất (không phân biệt miền): `scripts/build_unified_manifest.py` → `data/splits/unified/`.
  QIPEDC chia theo **bản quay** (`data/splits/recording_groups.csv`), VSL-GH chia theo **người ký** (S01–S04 / S05 / S06).
- Guard `DuplicateRecordingLeakageError` (`src/data/vsl_dataset.py`) chặn mọi split để cùng một bản quay ở hai phía.
- Cấp 1: chỉ dữ liệu quay thật (hauuto 4 người, 29 chữ + 5 dấu thanh); `data/vsl_alphabet_pilot` là dữ liệu tổng hợp, không dùng.
- `train_unified.py` dừng hẳn (FAIL) nếu một nhóm bản quay QIPEDC nằm ở hai tập, thiếu `recording_group`,
  bỏ qua kiểm tra trùng bản quay, hoặc S06 xuất hiện ngoài test (`assert_split_integrity`).

## Ghi chú hạ tầng — lần trích xuất sau (chưa áp dụng)
`extract_qipedc` (4.362 video) chạy > 5 giờ vì mỗi video tạo một phiên MediaPipe mới (nạp lại graph + model).
Lần sau: mỗi worker giữ **một** phiên `Holistic`/`Hands` và gọi `.reset()` (`SolutionBase.reset`, có trong
mediapipe 0.10.14: đóng và khởi động lại graph run) trước mỗi video, để tracker không mang vị trí tay của clip trước
sang clip sau. Trước khi dùng, đo lại: (1) thời gian/video so với phiên mới, (2) landmark của 20 video giống hệt
cách cũ (`np.allclose`); nếu `reset()` không giữ được model đã nạp thì lợi ích nhỏ, giữ cách cũ.

## Colab (tương tác)
Dùng qua Colab MCP khi cần thử nhanh với GPU T4: mở tab Colab (runtime T4), rồi trong Claude Code gọi
`open_colab_browser_connection`. Trích landmark trên Colab phải dùng env Python 3.11 + mediapipe 0.10.14 (xem skill).
