"""Interactive CLI to run processing tasks on the exporter `output/` directory.

Features:
- Scan `output/full_dump/` for org IDs and let the user pick one (or `all`).
- Run event/session/lap/announcement extractors and import to SQLite.
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


def process_all(org_dir: Path, formats: List[str], data_types: List[str], do_sqlite: bool = True) -> None:
    # locate files
    files = {
        "events": org_dir / "events.ndjson.gz",
        "laps": org_dir / "laps.ndjson.gz",
        "sessions": org_dir / "sessions.ndjson.gz",
        "announcements": org_dir / "announcements.ndjson.gz",
    }

    scripts_dir = HERE
    for dtype in data_types:
        in_path = files.get(dtype)
        if not in_path or not in_path.exists():
            print(f"No {dtype}.ndjson.gz found in {org_dir}")
            continue

        for fmt in formats:
            if fmt == "csv":
                if dtype == "events":
                    out = org_dir / "events_flat.csv"
                    rc = run_script(scripts_dir / "extract_events_to_csv.py", ["--input", str(org_dir), "--out", str(out)])
                elif dtype == "laps":
                    out = org_dir / "laps_flat.csv"
                    rc = run_script(scripts_dir / "extract_laps_to_csv.py", ["--input", str(org_dir), "--out", str(out)])
                elif dtype == "sessions":
                    out = org_dir / "sessions_flat.csv"
                    rc = run_script(scripts_dir / "extract_sessions_to_csv.py", ["--input", str(org_dir), "--out", str(out)])
                elif dtype == "announcements":
                    out = org_dir / "announcements_flat.csv"
                    rc = run_script(scripts_dir / "extract_announcements_to_csv.py", ["--input", str(org_dir), "--out", str(out)])
                else:
                    rc = 0
                if rc != 0:
                    print(f"CSV extractor for {dtype} failed", rc)

            elif fmt in ("sqlite", "db"):
                # ndjson_to_sqlite supports tables selection
                db_path = org_dir / "dump.db"
                rc = run_script(scripts_dir / "ndjson_to_sqlite.py", ["--input", str(in_path), "--out", str(db_path), "--tables", dtype])
                if rc != 0:
                    print(f"SQLite import for {dtype} failed", rc)

            elif fmt == "json":
                # convert ndjson.gz -> single JSON array
                out_json = org_dir / f"{dtype}.json"
                rc = convert_ndjson_to_json(in_path, out_json)
                if rc != 0:
                    print(f"JSON conversion for {dtype} failed", rc)

            elif fmt == "ndjson":
                # leave as-is or copy file
                print(f"NDJSON kept at {in_path}")
            else:
                print(f"Unknown format: {fmt}")


def convert_ndjson_to_json(in_path: Path, out_path: Path) -> int:
    # Streaming conversion: write a JSON array without loading into memory
    import gzip, json

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with gzip.open(in_path, "rt", encoding="utf8") as inf, out_path.open("w", encoding="utf8") as outf:
            outf.write("[")
            first = True
            for line in inf:
                if not line.strip():
                    continue
                obj = json.loads(line)
                if not first:
                    outf.write(",\n")
                else:
                    first = False
                json.dump(obj, outf)
            outf.write("]")
        return 0
    except Exception as exc:
        print("Error converting to JSON:", exc)
        return 2


def interactive(output_root: Path, org: Optional[Path] = None, preset_formats: Optional[List[str]] = None, preset_data_types: Optional[List[str]] = None, preset_no_sqlite: Optional[bool] = None) -> None:
    orgs = find_org_dirs(output_root)
    if not orgs:
        print("No org directories found under", output_root)
        return
    print("Found org directories:")
    for i, d in enumerate(orgs, start=1):
        print(f"  {i}) {d.name}")
    print("  a) all")
    # determine which org(s) to process
    if org is not None:
        targets = [org]
    else:
        choice = input("Select org number (or 'a' for all): ").strip()
        if choice.lower().startswith("a"):
            targets = orgs
        else:
            try:
                idx = int(choice) - 1
                targets = [orgs[idx]]
            except Exception as exc:
                print("Invalid selection:", exc)
                return

    # ask for formats and data types if not preset
    def ask_formats() -> List[str]:
        opts = ["csv", "json", "ndjson", "sqlite"]
        print("Select output formats (comma-separated):")
        for i, v in enumerate(opts, start=1):
            print(f"  {i}) {v}")
        print("  a) all")
        resp = input("Formats [1,2 or a for all] (default: all): ").strip()
        if not resp or resp.lower().startswith("a"):
            return opts
        picks = []
        for part in resp.split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(opts):
                    picks.append(opts[idx])
            else:
                if part in opts:
                    picks.append(part)
        return picks or opts

    def ask_data_types() -> List[str]:
        opts = ["events", "laps", "sessions", "announcements"]
        print("Select data types to process (comma-separated):")
        for i, v in enumerate(opts, start=1):
            print(f"  {i}) {v}")
        print("  a) all")
        resp = input("Data types [1,2 or a for all] (default: all): ").strip()
        if not resp or resp.lower().startswith("a"):
            return opts
        picks = []
        for part in resp.split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(opts):
                    picks.append(opts[idx])
            else:
                if part in opts:
                    picks.append(part)
        return picks or opts

    formats = preset_formats if preset_formats is not None else ask_formats()
    data_types = preset_data_types if preset_data_types is not None else ask_data_types()
    no_sqlite = preset_no_sqlite if preset_no_sqlite is not None else (input("Skip sqlite import? [y/N]: ").strip().lower() == "y")

    for d in targets:
        print(f"Processing {d} -> formats={formats} data={data_types} sqlite={not no_sqlite}")
        process_all(d, formats=formats, data_types=data_types, do_sqlite=not no_sqlite)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Processing CLI: run extractors on output/full_dump/<org>")
    p.add_argument("--output-root", type=Path, default=Path("output/full_dump"), help="Root directory containing org output dirs")
    p.add_argument("--org", type=str, help="Org ID directory to process (e.g. 30476)")
    p.add_argument("--run-all", action="store_true", help="Run all processing steps (laps/sessions/announcements/import)")
    p.add_argument("--no-sqlite", action="store_true", help="Skip SQLite import step")
    p.add_argument("--format", "-f", action="append", choices=["csv", "json", "ndjson", "sqlite", "db"], help="output format(s) to produce (can be specified multiple times)")
    p.add_argument("--data", "-d", action="append", choices=["events", "laps", "sessions", "announcements"], help="which data types to process (can be specified multiple times)")
    args = p.parse_args(argv)

    outroot = args.output_root
    if args.org:
        orgdir = outroot / args.org
        if not orgdir.exists():
            print("Org directory not found:", orgdir)
            return 2
        # if user provided formats/data flags use them, otherwise prompt interactively for this org
        if args.format or args.data:
            formats = args.format or ["csv", "json", "ndjson"]
            data_types = args.data or ["events", "laps", "sessions", "announcements"]
            process_all(orgdir, formats=formats, data_types=data_types, do_sqlite=not args.no_sqlite)
        else:
            interactive(outroot, org=orgdir, preset_formats=None, preset_data_types=None, preset_no_sqlite=args.no_sqlite)
        return 0

    # no org specified on CLI -> decide interactive vs preset-driven
    if args.format or args.data or args.run_all:
        formats = args.format or ["csv", "json", "ndjson"]
        data_types = args.data or ["events", "laps", "sessions", "announcements"]
        if args.run_all:
            for d in find_org_dirs(outroot):
                process_all(d, formats=formats, data_types=data_types, do_sqlite=not args.no_sqlite)
            return 0
        # prompt for which org but use presets for formats/data
        interactive(outroot, preset_formats=formats, preset_data_types=data_types, preset_no_sqlite=args.no_sqlite)
        return 0

    # default: fully interactive flow (no flags passed)
    interactive(outroot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
