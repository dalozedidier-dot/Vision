#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def verify_unified_manifest(cycle_dir: Path) -> None:
    mpath = cycle_dir / "unified_manifest.json"
    if not mpath.exists():
        raise SystemExit(f"missing {mpath}")
    m = json.loads(mpath.read_text(encoding="utf-8"))
    for a in m.get("artifacts", []):
        rel = a["path"]
        p = cycle_dir / rel
        if not p.exists():
            raise SystemExit(f"missing artifact: {rel}")
        got = sha256_file(p)
        exp = a["sha256"]
        if got != exp:
            raise SystemExit(f"hash mismatch for {rel}: got {got} expected {exp}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Path under repo, e.g. test_data/GDPDeflator.csv")
    ap.add_argument("--mode", choices=["mock", "real"], default="mock")
    ap.add_argument("--out-fixtures", default="shared_fixtures")
    ap.add_argument("--out-cycles", default="unified_cycles")
    ap.add_argument("--label", default="sample")
    args = ap.parse_args()

    f = Path(args.file)
    if not f.exists():
        raise SystemExit(f"file not found: {f}")

    # 1) fixture
    subprocess.check_call([
        "python3", "tools/collector.py",
        "--out", args.out_fixtures,
        "--source", f"{args.label}:{str(f)}",
    ])

    # last created cycle_id
    fixtures_root = Path(args.out_fixtures)
    cycle_id = sorted([p.name for p in fixtures_root.iterdir() if p.is_dir()])[-1]

    # 2) optional: enable SystemD from CSV if tool exists and mode=real
    if args.mode == "real":
        csv_to_tm = Path("tools/csv_to_test_matrix.py")
        if csv_to_tm.exists() and f.suffix.lower() == ".csv":
            raw_csv = fixtures_root / cycle_id / "raw" / f.name
            tm = fixtures_root / cycle_id / "raw" / "TEST_MATRIX.md"
            if raw_csv.exists():
                subprocess.check_call([
                    "python3", str(csv_to_tm),
                    "--csv", str(raw_csv),
                    "--out", str(tm),
                ])

    # 3) run
    if args.mode == "mock":
        subprocess.check_call(["bash", "tools/run_parallel.sh", str(fixtures_root / cycle_id), args.out_cycles])
    else:
        subprocess.check_call(["bash", "tools/run_parallel_real.sh", str(fixtures_root / cycle_id), args.out_cycles])

    # 4) verify
    cycle_dir = Path(args.out_cycles) / cycle_id
    verify_unified_manifest(cycle_dir)

    print(cycle_id)

if __name__ == "__main__":
    main()
