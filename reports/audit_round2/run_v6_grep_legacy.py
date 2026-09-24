import os
import sys
import io
import json
import re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)

print("=== STARTING V6: GREP FOR OBSOLETE CONFIGURATIONS & MOCK CODE ===")

PATTERNS = {
    "tier2_train.csv": r"tier2_train\.csv",
    "tier2_val.csv": r"tier2_val\.csv",
    "tier2_test.csv": r"tier2_test\.csv",
    "num_classes_489": r"\b489\b",
    "math_random": r"Math\.random",
    "acc_98.06": r"98\.06",
    "asl_reference": r"\bASL\b|\basl_alphabet\b",
}

EXCLUDE_DIRS = {".git", ".venv", "node_modules", ".gitnexus", "reports", "scratch"}
EXCLUDE_EXTS = {".pt", ".pth", ".onnx", ".npy", ".npz", ".png", ".jpg", ".jpeg", ".mp4", ".safetensors", ".bin", ".pyc"}

findings = {k: [] for k in PATTERNS}

for root, dirs, files in os.walk(PROJECT_ROOT):
    # filter dirs
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in EXCLUDE_EXTS:
            continue
        filepath = os.path.join(root, file)
        rel_path = os.path.relpath(filepath, PROJECT_ROOT).replace("\\", "/")
        
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    for pat_name, pat_regex in PATTERNS.items():
                        if re.search(pat_regex, line):
                            findings[pat_name].append({
                                "file": rel_path,
                                "line": line_num,
                                "content": line.strip()[:150]
                            })
        except Exception:
            pass

print("\n--- GREP FINDINGS SUMMARY ---")
for k, matches in findings.items():
    print(f"[{k}] - {len(matches)} occurrences")
    for m in matches[:5]:
        print(f"  {m['file']}:{m['line']} -> {m['content']}")
    if len(matches) > 5:
        print(f"  ... and {len(matches) - 5} more")

with open('reports/audit_round2/v6_legacy_grep_findings.json', 'w', encoding='utf-8') as f:
    json.dump(findings, f, indent=2, ensure_ascii=False)

print("\nV6 completed and saved to reports/audit_round2/v6_legacy_grep_findings.json.")
