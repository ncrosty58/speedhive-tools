#!/usr/bin/env python3
"""Speedhive Tools CLI – unified entry point."""

import argparse
import os
import sys
from pathlib import Path

from speedhive.cli.discovery import register_discovered


def default_db_path() -> Path:
    return Path(os.environ.get("SPEEDHIVE_DB_PATH", "./web_data/speedhive.db"))


def _run_module_as_main(module_name: str, args):
    import importlib
    mod = importlib.import_module(module_name)
    if hasattr(mod, "main") and callable(mod.main):
        return mod.main(argv=args)
    raise RuntimeError(f"Module {module_name} has no main(argv)")


def _export_full_dump(args):
    argv = ["--org", str(args.org), "--output", str(args.output)]
    if args.verbose:
        argv.append("--verbose")
    if args.no_resume:
        argv.append("--no-resume")
    if args.max_events:
        argv.extend(["--max-events", str(args.max_events)])
    if args.concurrency != 5:
        argv.extend(["--concurrency", str(args.concurrency)])
    return _run_module_as_main("speedhive.exporters.export_full_dump", argv)


def _report_consistency(args):
    argv = ["--org", str(args.org)]
    if args.db_path != default_db_path():
        argv.extend(["--db-path", str(args.db_path)])
    if args.dump_dir != "./output":
        argv.extend(["--dump-dir", str(args.dump_dir)])
    if args.out_dir != "./output":
        argv.extend(["--out-dir", str(args.out_dir)])
    if args.min_laps != 20:
        argv.extend(["--min-laps", str(args.min_laps)])
    if args.top != 10:
        argv.extend(["--top", str(args.top)])
    if args.threshold != 0.85:
        argv.extend(["--threshold", str(args.threshold)])
    if args.driver:
        argv.extend(["--driver", args.driver])
    return _run_module_as_main("speedhive.analyzers.analyze_consistency", argv)


def _extract_driver_laps(args):
    argv = ["--org", str(args.org), "--driver", args.driver]
    if args.driver_keys:
        argv.extend(["--driver-keys", args.driver_keys])
    if args.db_path != default_db_path():
        argv.extend(["--db-path", str(args.db_path)])
    if args.dump_dir != Path("./output"):
        argv.extend(["--dump-dir", str(args.dump_dir)])
    if args.out_dir != Path("./output"):
        argv.extend(["--out-dir", str(args.out_dir)])
    if args.threshold != 0.8:
        argv.extend(["--threshold", str(args.threshold)])
    if args.min_laps != 1:
        argv.extend(["--min-laps", str(args.min_laps)])
    return _run_module_as_main("speedhive.analyzers.analyze_driver_laps", argv)


def _extract_track_records(args):
    argv = ["--org", str(args.org)]
    if args.classification:
        argv.extend(["--classification", args.classification])
    if args.db_path != default_db_path():
        argv.extend(["--db-path", str(args.db_path)])
    if args.dump_dir != Path("./output"):
        argv.extend(["--dump-dir", str(args.dump_dir)])
    if args.output:
        argv.extend(["--output", str(args.output)])
    return _run_module_as_main("speedhive.processing.process_track_records", argv)


def _build_sync_argv(args) -> list[str]:
    argv = ["--org", str(args.org), "--db-path", str(args.db_path), "--mode", args.mode]
    if args.max_events is not None:
        argv.extend(["--max-events", str(args.max_events)])
    if args.recent_backfill_events:
        argv.extend(["--recent-backfill-events", str(args.recent_backfill_events)])
    if args.token:
        argv.extend(["--token", args.token])
    return argv


def _sync_org(args):
    argv = _build_sync_argv(args)
    return _run_module_as_main("speedhive.exporters.export_org_cache", argv)


def _import_dump(args):
    argv = ["--org", str(args.org)]
    if args.db_path != default_db_path():
        argv.extend(["--db-path", str(args.db_path)])
    if args.dump_dir != Path("./output"):
        argv.extend(["--dump-dir", str(args.dump_dir)])
    return _run_module_as_main("speedhive.processing.process_sqlite_import", argv)


def main():
    parser = argparse.ArgumentParser(description="Speedhive Tools")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("export-dump", help="Export a raw offline NDJSON dump for an organization")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--output", default="./output", help="Root output directory for NDJSON dump files")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--max-events", type=int, default=None)
    p.add_argument("--concurrency", type=int, default=5)
    p.set_defaults(func=_export_full_dump)

    p = sub.add_parser("report-consistency", help="Report top/bottom consistency from the primary SQLite cache")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    p.add_argument("--dump-dir", default="./output", help="Legacy offline dump root used only when the DB has no org data")
    p.add_argument("--out-dir", default="./output", help="Output directory for generated reports")
    p.add_argument("--min-laps", type=int, default=20)
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--threshold", type=float, default=0.85)
    p.add_argument("--driver", default=None)
    p.set_defaults(func=_report_consistency)

    p = sub.add_parser("extract-driver-laps", help="Extract laps for a driver from the primary SQLite cache")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--driver", required=True, help="Driver name to fuzzy match")
    p.add_argument("--driver-keys", default=None)
    p.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    p.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Legacy offline dump root used only when the DB has no org data")
    p.add_argument("--out-dir", type=Path, default=Path("./output"), help="Output directory for generated reports")
    p.add_argument("--threshold", type=float, default=0.8)
    p.add_argument("--min-laps", type=int, default=1)
    p.set_defaults(func=_extract_driver_laps)

    p = sub.add_parser("extract-track-records", help="Extract track records from the primary SQLite cache to JSON")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--classification", default=None)
    p.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    p.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Legacy offline dump root used only when the DB has no org data")
    p.add_argument("--output", default=None, help="Output file path (JSON)")
    p.set_defaults(func=_extract_track_records)

    p = sub.add_parser("sync-org", help="Sync org data into the primary SQLite cache")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    p.add_argument("--mode", choices=["full", "incremental"], default="incremental")
    p.add_argument("--max-events", type=int, default=None)
    p.add_argument("--recent-backfill-events", type=int, default=0)
    p.add_argument("--token", default=None)
    p.set_defaults(func=_sync_org)

    p = sub.add_parser("import-dump", help="Import an offline NDJSON dump into the primary SQLite cache")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    p.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Root directory containing exported NDJSON dump files")
    p.set_defaults(func=_import_dump)

    register_discovered(sub)

    args = parser.parse_args()
    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
