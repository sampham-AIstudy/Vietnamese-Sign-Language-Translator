"""
Unified isolated-sign label inventory across every real source in data/ (dialect-agnostic).

The product targets signers nationwide, so regional variants of a word are one label: the
B/T/N variants of a QIPEDC word become several samples of the same class, and "(bắc)"-style
suffixes are stripped. Evaluation needs *independent* samples, so counts are of independent units:
  - QIPEDC  : distinct recording groups (data/splits/recording_groups.csv) — re-captioned copies = 1
  - HCMUE   : each crawled video (tudienngonngukyhieu.com, different signers from QIPEDC)
  - VSL-GH  : distinct signers (S01..S06) for a gloss segment cut from continuous sentences
Output: data/splits/label_inventory.csv, data/splits/label_inventory_summary.json
Usage:  python scripts/build_label_inventory.py
"""
import csv
import json
import os
import re
import unicodedata
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REGION_WORDS = r"(bắc|trung|nam|miền bắc|miền trung|miền nam|hà nội|hồ chí minh|tp\.? ?hcm|sài gòn|huế|hải phòng|đà nẵng|cần thơ)"


def normalize_label(text: str) -> str:
    s = unicodedata.normalize("NFC", str(text)).strip().lower()
    s = s.replace("-", " ").replace("_", " ")
    s = re.sub(r"\s*\(\s*" + REGION_WORDS + r"\s*\)\s*$", "", s)  # drop trailing regional suffix only
    return re.sub(r"\s+", " ", s).strip()


def main():
    units = defaultdict(lambda: {"qipedc_recordings": set(), "qipedc_videos": 0, "hcmue_videos": 0,
                                 "vslgh_signers": set(), "vslgh_segments": 0, "surface_forms": set()})

    with open(os.path.join(ROOT, "data", "splits", "recording_groups.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            u = units[normalize_label(r["gloss"])]
            u["qipedc_recordings"].add(r["recording_group"]); u["qipedc_videos"] += 1; u["surface_forms"].add(r["gloss"])

    with open(os.path.join(ROOT, "data", "raw_tudienngonngukyhieu", "metadata.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if os.path.exists(os.path.join(ROOT, "data", "raw_tudienngonngukyhieu", "videos", r["video_filename"])):
                u = units[normalize_label(r["gloss"])]
                u["hcmue_videos"] += 1; u["surface_forms"].add(r["gloss"])

    with open(os.path.join(ROOT, "data", "external", "vsl_gh", "dataset_canonical.json"), encoding="utf-8") as f:
        for s in json.load(f):
            for g in s.get("glosses_detail", []):
                u = units[normalize_label(g["gloss"])]
                u["vslgh_signers"].add(s["signer_id"]); u["vslgh_segments"] += 1; u["surface_forms"].add(g["gloss"])

    rows = []
    for label, u in sorted(units.items()):
        independent = len(u["qipedc_recordings"]) + u["hcmue_videos"] + len(u["vslgh_signers"])
        rows.append({
            "label": label, "independent_units": independent,
            "qipedc_recordings": len(u["qipedc_recordings"]), "qipedc_videos": u["qipedc_videos"],
            "hcmue_videos": u["hcmue_videos"], "vslgh_signers": len(u["vslgh_signers"]),
            "vslgh_segments": u["vslgh_segments"],
            "sources": "+".join(k for k, v in (("qipedc", u["qipedc_videos"]), ("hcmue", u["hcmue_videos"]),
                                               ("vslgh", u["vslgh_segments"])) if v),
            "surface_forms": " | ".join(sorted(u["surface_forms"])),
        })
    out = os.path.join(ROOT, "data", "splits", "label_inventory.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    def count(pred):
        return sum(1 for r in rows if pred(r))
    summary = {
        "labels_total": len(rows),
        "labels_by_source": {s: count(lambda r, s=s: s in r["sources"].split("+")) for s in ("qipedc", "hcmue", "vslgh")},
        "labels_in_2plus_sources": count(lambda r: "+" in r["sources"]),
        "independent_units_ge": {k: count(lambda r, k=k: r["independent_units"] >= k) for k in (1, 2, 3, 5, 6)},
        "train_only_labels_(1_unit)": count(lambda r: r["independent_units"] == 1),
        "note": "Labels with >=2 independent units can be trained AND tested on an unseen recording; "
                ">=3 also allow a validation sample. 1-unit labels can be trained but never measured.",
    }
    json.dump(summary, open(os.path.join(ROOT, "data", "splits", "label_inventory_summary.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
