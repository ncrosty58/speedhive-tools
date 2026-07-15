#!/usr/bin/env python3
"""Speedhive Tools CLI – unified entry point."""

import argparse
import json
import os
import sys
from pathlib import Path

from speedhive.cli.discovery import register_discovered
from speedhive.exporters.export_curated_track_records import export_curated_track_records_ndjson
from speedhive.processing.track_records_import import import_curated_track_records_ndjson
from speedhive.wrapper import SpeedhiveClient


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
    if args.ignore_outliers:
        argv.append("--ignore-outliers")
    return _run_module_as_main("speedhive.analyzers.analyze_consistency", argv)


def _extract_driver_laps(args):
    argv = ["--org", str(args.org), "--driver", args.driver]
    if args.driver_keys:
        argv.extend(["--driver-keys", args.driver_keys])
    if args.db_path != default_db_path():
        argv.extend(["--db-path", str(args.db_path)])
    if args.out_dir != Path("./output"):
        argv.extend(["--out-dir", str(args.out_dir)])
    if args.threshold != 0.8:
        argv.extend(["--threshold", str(args.threshold)])
    if args.min_laps != 1:
        argv.extend(["--min-laps", str(args.min_laps)])
    if args.ignore_outliers:
        argv.append("--ignore-outliers")
    return _run_module_as_main("speedhive.analyzers.analyze_driver_laps", argv)


def _extract_track_records(args):
    argv = ["--org", str(args.org)]
    if args.classification:
        argv.extend(["--classification", args.classification])
    if args.db_path != default_db_path():
        argv.extend(["--db-path", str(args.db_path)])
    if args.output:
        argv.extend(["--output", str(args.output)])
    return _run_module_as_main("speedhive.exporters.export_track_records", argv)


def _export_curated_track_records(args):
    body = export_curated_track_records_ndjson(args.org, args.track_records_root)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(body, encoding="utf-8")
    else:
        sys.stdout.write(body)
    return 0


def _import_curated_track_records(args):
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Error: input file does not exist at '{in_path}'.", file=sys.stderr)
        return 1
    try:
        notice = import_curated_track_records_ndjson(
            args.org,
            args.track_records_root,
            in_path.read_text(encoding="utf-8"),
            replace=args.mode == "replace",
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(notice)
    return 0


def _scan_track_records(args):
    from speedhive.processing import track_records_curation as track_records

    result = track_records.run_sync_and_diff(args.org, args.db_path, args.track_records_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _refresh_track_records(args):
    from speedhive.processing import track_records_curation as track_records

    client = SpeedhiveClient.create()
    outcome = track_records.refresh_and_scan(
        args.org,
        client,
        args.db_path,
        args.track_records_root,
        mode=args.mode,
        force=args.force,
        max_events=args.max_events,
        recent_backfill_events=args.recent_backfill_events,
        cleanup_on_full=not args.no_cleanup_on_full,
    )
    print(json.dumps(outcome, indent=2, sort_keys=True))
    return 0


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
    return _run_module_as_main("speedhive.processing.refresh_org_cache", argv)


def _import_dump(args):
    argv = ["--org", str(args.org)]
    if args.db_path != default_db_path():
        argv.extend(["--db-path", str(args.db_path)])
    if args.dump_dir != Path("./output"):
        argv.extend(["--dump-dir", str(args.dump_dir)])
    return _run_module_as_main("speedhive.processing.process_sqlite_import", argv)


def _export_lap_records(args):
    argv = ["--org", str(args.org)]
    if args.max_events:
        argv.extend(["--max-events", str(args.max_events)])
    if args.db_path != default_db_path():
        argv.extend(["--db-path", str(args.db_path)])
    if args.output:
        argv.extend(["--output", str(args.output)])
    return _run_module_as_main("speedhive.exporters.export_lap_records", argv)


def _export_db_dump(args):
    argv = ["--org", str(args.org), "--output-dir", str(args.output_dir)]
    if args.db_path != default_db_path():
        argv.extend(["--db-path", str(args.db_path)])
    if args.max_events is not None:
        argv.extend(["--max-events", str(args.max_events)])
    return _run_module_as_main("speedhive.exporters.export_db_dump", argv)


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
    p.add_argument("--out-dir", default="./output", help="Output directory for generated reports")
    p.add_argument("--min-laps", type=int, default=20)
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--threshold", type=float, default=0.85)
    p.add_argument("--driver", default=None)
    p.add_argument("--ignore-outliers", action="store_true", help="Ignore outlier lap times using IQR method")
    p.set_defaults(func=_report_consistency)

    p = sub.add_parser("extract-driver-laps", help="Extract laps for a driver from the primary SQLite cache")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--driver", required=True, help="Driver name to fuzzy match")
    p.add_argument("--driver-keys", default=None)
    p.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    p.add_argument("--out-dir", type=Path, default=Path("./output"), help="Output directory for generated reports")
    p.add_argument("--threshold", type=float, default=0.8)
    p.add_argument("--min-laps", type=int, default=1)
    p.add_argument("--ignore-outliers", action="store_true", help="Ignore outlier lap times using IQR method")
    p.set_defaults(func=_extract_driver_laps)

    p = sub.add_parser("export-track-records", help="Export track records from the primary SQLite cache to NDJSON")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--classification", default=None)
    p.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    p.add_argument("--output", default=None, help="Output file path (NDJSON)")
    p.set_defaults(func=_extract_track_records)

    p = sub.add_parser("export-curated-track-records", help="Export curated track records from the workflow store to NDJSON")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--track-records-root", type=Path, default=Path("./web_data/track_records"), help="Track-record workflow storage root")
    p.add_argument("--output", default=None, help="Output file path (NDJSON)")
    p.set_defaults(func=_export_curated_track_records)

    p = sub.add_parser("import-curated-track-records", help="Import curated track records into the workflow store from NDJSON")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--track-records-root", type=Path, default=Path("./web_data/track_records"), help="Track-record workflow storage root")
    p.add_argument("--input", required=True, help="Input file path (NDJSON)")
    p.add_argument("--mode", choices=["merge", "replace"], default="merge")
    p.set_defaults(func=_import_curated_track_records)

    p = sub.add_parser("scan-track-records", help="Diff track records against the curated store without refreshing the org cache")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    p.add_argument("--track-records-root", type=Path, default=Path("./web_data/track_records"), help="Track-records storage root")
    p.set_defaults(func=_scan_track_records)

    p = sub.add_parser("refresh-track-records", help="Refresh the org cache if needed, then scan track records")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    p.add_argument("--track-records-root", type=Path, default=Path("./web_data/track_records"), help="Track-records storage root")
    p.add_argument("--mode", choices=["full", "incremental"], default="incremental")
    p.add_argument("--force", action="store_true", help="Refresh and scan even if the cache appears fresh")
    p.add_argument("--max-events", type=int, default=None, help="Maximum number of events to refresh")
    p.add_argument("--recent-backfill-events", type=int, default=20, help="Number of recent events to backfill in incremental mode")
    p.add_argument("--no-cleanup-on-full", action="store_true", help="Skip pruning removed events after a full refresh")
    p.set_defaults(func=_refresh_track_records)

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

    p = sub.add_parser("export-lap-records", help="Export lap records from the primary SQLite cache to NDJSON")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--max-events", type=int, default=25, help="Maximum number of events to export")
    p.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    p.add_argument("--output", "-o", default=None, help="Output NDJSON file path (default: stdout)")
    p.set_defaults(func=_export_lap_records)

    p = sub.add_parser("export-db-dump", help="Export an offline NDJSON dump of an organization from the primary SQLite cache")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--output-dir", type=Path, required=True, help="Directory to save NDJSON files")
    p.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    p.add_argument("--max-events", type=int, default=None, help="Maximum number of events to export")
    p.set_defaults(func=_export_db_dump)

    register_discovered(sub)

    args = parser.parse_args()
    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
