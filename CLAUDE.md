<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **Vietnamese-Sign-Language-Translator** (1120 symbols, 1834 relationships, 46 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/Vietnamese-Sign-Language-Translator/context` | Codebase overview, check index freshness |
| `gitnexus://repo/Vietnamese-Sign-Language-Translator/clusters` | All functional areas |
| `gitnexus://repo/Vietnamese-Sign-Language-Translator/processes` | All execution flows |
| `gitnexus://repo/Vietnamese-Sign-Language-Translator/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

## VSLT — khôi phục & trạng thái

Đây là dự án Vietnamese Sign Language Translator. Phiên làm việc có thể bị ngắt bất cứ lúc nào
(giới hạn API, thoát chương trình, nén context). Mọi thứ cần để tiếp tục nằm trong FILE, không nằm trong trí nhớ hội thoại.

### Khi bắt đầu phiên, hoặc khi người dùng nhắn "tiếp tục" / "continue"
0. Nếu `CLAUDE_CODE_REMOTE=true` (Claude Code on the web): đọc và làm mục 2 của `docs/CLOUD.md` trước (venv, npm ci, dữ liệu).
1. Đọc `docs/STATE.md` (trạng thái duy nhất cần tin), rồi `docs/progress_log.md` (10 dòng cuối). KHÔNG đọc `docs/STATE_archive.md`
   (lịch sử) trừ khi cần truy vết. Quy tắc tiết kiệm hạn mức: `docs/prompts/orchestrator_resume_addendum.md` mục 6.
2. Đối chiếu với thực tế, không tin STATE.md mù quáng:
   - `git status`, `git branch --show-current`, `git log --oneline -15`
   - `ls docs/plans docs/reviews`
   - nếu STATE.md ghi có Kaggle kernel đang chạy: kiểm tra trạng thái thật bằng `kaggle kernels status`
3. Nếu STATE.md và thực tế lệch nhau: sửa STATE.md cho đúng thực tế, ghi 1 dòng vào mục "Nhật ký khôi phục", rồi mới làm tiếp.
4. Đọc `docs/prompts/orchestrator.md` và `docs/prompts/orchestrator_resume_addendum.md`, làm theo.
5. KHÔNG làm lại việc đã APPROVE. KHÔNG hỏi người dùng lại những gì đã có trong mục "Quyết định của người dùng".

### Quy tắc cứng (tóm tắt, bản đầy đủ ở docs/prompts/autopilot.md mục 4)
- Không bịa số liệu; số liệu chỉ từ JSON có lệnh + commit hash.
- Không sửa/skip/nới test để pass; không đổi tiêu chí GATE sau khi thấy kết quả.
- Không đụng thay đổi chưa commit của người dùng; không đổi model mặc định ngoài GATE.
- Chỉ cài gói vào .venv / frontend/; không chạy script tải từ mạng.
- Train nặng chỉ trên Kaggle (private).
