---
name: vsl-handoff
description: Dùng ở ĐẦU mỗi phiên làm việc với dự án VSL (đọc handoff mới nhất thay vì dò lại repo) và ở CUỐI phiên / khi context dài (ghi handoff mới). Giúp tiếp tục công việc nhiều bước (kernel cloud đang chạy, commit dở, quyết định đã chốt) mà không tốn token khám phá lại.
---

# VSL handoffs

Thư mục: `.claude/handoffs/` — mỗi file `YYYY-MM-DD-<chủ-đề>.md`, file mới nhất là trạng thái hiện hành.

## Đầu phiên
1. Đọc file mới nhất trong `.claude/handoffs/` (chỉ file đó). Tin các số liệu/quyết định trong đó; chỉ kiểm lại thứ có thể đã đổi:
   `git log --oneline -5`, `git status -sb`, trạng thái kernel (`kaggle kernels status phmvnsm33/<kernel>`).
2. Không hỏi lại những gì mục "Decisions already made" đã chốt.

## Cuối phiên / trước khi context bị tóm tắt
Viết file handoff mới (không sửa file cũ — giữ lịch sử), ≤ ~80 dòng, gồm đúng các mục:
- **Goal** (1–3 dòng, lời chủ dự án rút gọn)
- **State** (bảng: việc / trạng thái / lệnh tiếp theo) — gồm kernel cloud đang chạy + ID
- **Next steps** theo thứ tự, mỗi bước có lệnh cụ thể
- **Key numbers** đã kiểm chứng (kèm đường dẫn artifact)
- **Commits** của phiên (hash + 3–5 từ)
- **Decisions already made** + điều **không** được làm khi chưa hỏi
- **Open caveats** (file có thay đổi chưa commit của chủ dự án, index GitNexus cũ, v.v.)
Rồi cập nhật dòng handoff trong memory index (`MEMORY.md`) trỏ tới file mới.

Không đưa vào handoff: token/secret, nội dung `~/.kaggle`, `mcpProxyToken` của Colab, dump log dài.
