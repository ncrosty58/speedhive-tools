"""Interactive CLI to run processing tasks on the exporter `output/` directory.

Features:
- Scan `output/full_dump/` for org IDs and let the user pick one (or `all`).
- Run session/lap/announcement extractors and import to SQLite.
- Non-interactive flags to run everything for a given org.

Usage (interactive):
  python examples/processing/processor_cli.py

Usage (non-interactive):
  python examples/processing/processor_cli.py --org 30476 --run-all --output output/full_dump/30476
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


HERE = Path(__file__).resolve().parent


def find_org_dirs(output_root: Path) -> List[Path]:
    p = output_root.expanduser()
    if not p.exists():
        return []
    return [d for d in sorted(p.iterdir()) if d.is_dir()]


def run_script(script: Path, args: List[str]) -> int:
    cmd = [sys.executable, str(script)] + args
    print(f"-> Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def process_all(org_dir: Path, do_sqlite: bool = True) -> None:
    # locate files
    laps = org_dir / "laps.ndjson.gz"
    sessions = org_dir / "sessions.ndjson.gz"
    announcements = org_dir / "announcements.ndjson.gz"

    scripts_dir = HERE
    if laps.exists():
        rc = run_script(scripts_dir / "extract_laps_to_csv.py", ["--input", str(org_dir), "--out", str(org_dir / "laps_flat.csv")])
        if rc != 0:
            print("extract_laps_to_csv.py failed", rc)
    else:
        print("No laps.ndjson.gz found in", org_dir)

    if sessions.exists():
        rc = run_script(scripts_dir / "extract_sessions_to_csv.py", ["--input", str(org_dir), "--out", str(org_dir / "sessions_flat.csv")])
        if rc != 0:
            print("extract_sessions_to_csv.py failed", rc)
    else:
        print("No sessions.ndjson.gz found in", org_dir)

    if announcements.exists():
        rc = run_script(scripts_dir / "extract_announcements_to_csv.py", ["--input", str(org_dir), "--out", str(org_dir / "announcements_flat.csv")])
        if rc != 0:
            print("extract_announcements_to_csv.py failed", rc)
    else:
        print("No announcements.ndjson.gz found in", org_dir)

    if do_sqlite and laps.exists():
        rc = run_script(scripts_dir / "ndjson_to_sqlite.py", ["--input", str(org_dir / "laps.ndjson.gz"), "--out", str(org_dir / "dump.db")])
        if rc != 0:
            print("ndjson_to_sqlite.py failed", rc)


def interactive(output_root: Path) -> None:
    orgs = find_org_dirs(output_root)
    if not orgs:
        print("No org directories found under", output_root)
        return
    print("Found org directories:")
    for i, d in enumerate(orgs, start=1):
        print(f"  {i}) {d.name}")
    print("  a) all")
    choice = input("Select org number (or 'a' for all): ").strip()
    if choice.lower().startswith("a"):
        for d in orgs:
            print(f"Processing {d}")
            process_all(d)
    else:
        try:
            idx = int(choice) - 1
            d = orgs[idx]
            process_all(d)
        except Exception as exc:
            print("Invalid selection:", exc)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Processing CLI: run extractors on output/full_dump/<org>")
    p.add_argument("--output-root", type=Path, default=Path("output/full_dump"), help="Root directory containing org output dirs")
    p.add_argument("--org", type=str, help="Org ID directory to process (e.g. 30476)")
    p.add_argument("--run-all", action="store_true", help="Run all processing steps (laps/sessions/announcements/import)")
    p.add_argument("--no-sqlite", action="store_true", help="Skip SQLite import step")
    args = p.parse_args(argv)

    outroot = args.output_root
    if args.org:
        orgdir = outroot / args.org
        if not orgdir.exists():
            print("Org directory not found:", orgdir)
            return 2
        if args.run_all:
            process_all(orgdir, do_sqlite=not args.no_sqlite)
        else:
            # interactive per-org choices
            print("Processing directory:", orgdir)
            process_all(orgdir, do_sqlite=not args.no_sqlite)
        return 0

    # no org specified -> interactive selection
    interactive(outroot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
