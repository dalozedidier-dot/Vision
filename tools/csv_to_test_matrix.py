#!/usr/bin/env python3
"""CSV -> TEST_MATRIX.md generator for SystemD.

Goal:
- Produce a deterministic Markdown file with headings + list items so SystemD's DDR parser can ingest it.
- No external deps (stdlib only).

Usage:
  python3 tools/csv_to_test_matrix.py --csv path/to/file.csv --out shared_fixtures/<cycle_id>/raw/TEST_MATRIX.md

Notes:
- This is descriptive only. It does not infer meaning.
- It samples the first N rows (default 50) for "ROWS_SAMPLE".
"""

import argparse
import csv
import hashlib
import statistics
from pathlib import Path

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Input CSV path")
    ap.add_argument("--out", required=True, help="Output Markdown path (suggest: raw/TEST_MATRIX.md)")
    ap.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")
    ap.add_argument("--sample-rows", type=int, default=50, help="How many rows to sample for ROWS_SAMPLE")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f, delimiter=args.delimiter)
        try:
            header = next(reader)
        except StopIteration:
            raise SystemExit("Empty CSV")

        header = [h.strip() for h in header]
        rows = []
        for i, r in enumerate(reader):
            rows.append(r)
            if i + 1 >= args.sample_rows:
                break

    ncols = len(header)
    nrows_sample = len(rows)

    # Basic per-column stats on sample
    col_stats = []
    for ci, name in enumerate(header):
        values = []
        missing = 0
        numeric = 0
        for r in rows:
            v = r[ci].strip() if ci < len(r) else ""
            if v == "" or v.lower() in {"na", "nan", "null", "none"}:
                missing += 1
                continue
            values.append(v)
            if is_number(v):
                numeric += 1

        stat = {
            "col": name if name else f"col_{ci+1}",
            "missing": missing,
            "present": len(values),
            "numeric_like": numeric,
        }
        # numeric summary if mostly numeric in sample
        nums = [float(v) for v in values if is_number(v)]
        if nums and (len(nums) >= max(3, int(0.6 * len(values)))):
            try:
                stat["min"] = min(nums)
                stat["max"] = max(nums)
                stat["mean"] = statistics.mean(nums)
                stat["median"] = statistics.median(nums)
            except Exception:
                pass
        col_stats.append(stat)

    # Deterministic markdown
    lines = []
    lines.append("# TEST_MATRIX — generated from CSV (TransObserver)")
    lines.append("")
    lines.append("## META")
    lines.append(f"- csv_file: {csv_path.name}")
    lines.append(f"- csv_sha256: {sha256_file(csv_path)}")
    lines.append(f"- delimiter: {args.delimiter}")
    lines.append(f"- sample_rows: {args.sample_rows}")
    lines.append(f"- sample_rows_read: {nrows_sample}")
    lines.append(f"- columns: {ncols}")
    lines.append("")
    lines.append("## COLUMNS")
    for ci, name in enumerate(header, start=1):
        nm = name if name else f"col_{ci}"
        lines.append(f"- {ci}. {nm}")
    lines.append("")
    lines.append("## COLUMN_STATS_SAMPLE")
    for st in col_stats:
        nm = st["col"]
        parts = [f"present={st.get('present',0)}", f"missing={st.get('missing',0)}", f"numeric_like={st.get('numeric_like',0)}"]
        if "min" in st:
            parts.append(f"min={st['min']}")
            parts.append(f"max={st['max']}")
            parts.append(f"mean={st['mean']}")
            parts.append(f"median={st['median']}")
        lines.append(f"- {nm}: " + ", ".join(parts))
    lines.append("")
    lines.append("## ROWS_SAMPLE")
    # Render rows as stable key=value pairs
    for ri, r in enumerate(rows, start=1):
        pairs = []
        for ci, name in enumerate(header):
            nm = name if name else f"col_{ci+1}"
            v = r[ci].strip() if ci < len(r) else ""
            # avoid newlines
            v = v.replace("\n", " ").replace("\r", " ").strip()
            if len(v) > 120:
                v = v[:120] + "…"
            pairs.append(f"{nm}={v}")
        lines.append(f"- row_{ri}: " + " | ".join(pairs))

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(out_path))

if __name__ == "__main__":
    main()
