#!/usr/bin/env python3
"""Speedhive Tools CLI - Unified command-line interface for Speedhive data tools."""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Speedhive Tools - Utilities for MyLaps Event Results API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  speedhive export-full-dump --org 30476 --output ./output/full_dump
  speedhive process-full-dump --org 30476
  speedhive extract-driver-laps --org 30476 --driver "Nathan Crosty"
  speedhive report-consistency --org 30476
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Export full dump
    export_parser = subparsers.add_parser(
        'export-full-dump',
        help='Export complete data dump for an organization'
    )
    export_parser.add_argument('--org', type=int, required=True, help='Organization ID')
    export_parser.add_argument('--output', type=Path, default=Path('./output/full_dump'),
                              help='Output directory (default: ./output/full_dump)')
    export_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    export_parser.add_argument('--no-resume', action='store_true', help='Do not resume from existing files')
    export_parser.add_argument('--max-events', type=int, help='Limit number of events to export')
    export_parser.add_argument('--concurrency', type=int, default=5, help='Concurrent requests (default: 5)')

    # Process full dump
    process_parser = subparsers.add_parser(
        'process-full-dump',
        help='Process raw dump data into aggregated files'
    )
    process_parser.add_argument('--org', type=int, required=True, help='Organization ID')
    process_parser.add_argument('--dump-dir', type=Path, default=Path('./output/full_dump'),
                               help='Input dump directory (default: ./output/full_dump)')
    process_parser.add_argument('--out-dir', type=Path, default=Path('./output'),
                               help='Output directory (default: ./output)')

    # Extract driver laps
    extract_parser = subparsers.add_parser(
        'extract-driver-laps',
        help='Extract lap data for a specific driver'
    )
    extract_parser.add_argument('--org', type=int, required=True, help='Organization ID')
    extract_parser.add_argument('--driver', '--name', required=True, help='Driver name to search for')
    extract_parser.add_argument('--driver-keys', help='Comma-separated driver_key values (skip fuzzy matching)')
    extract_parser.add_argument('--dump-dir', type=Path, default=Path('./output/full_dump'),
                               help='Dump directory (default: ./output/full_dump)')
    extract_parser.add_argument('--out-dir', type=Path, default=Path('./output'),
                               help='Output directory (default: ./output)')
    extract_parser.add_argument('--threshold', type=float, default=0.8, help='Fuzzy match threshold (default: 0.8)')
    extract_parser.add_argument('--min-laps', type=int, default=1, help='Minimum lap count (default: 1)')

    # Report driver consistency
    consistency_parser = subparsers.add_parser(
        'report-consistency',
        help='Report top/bottom most consistent drivers'
    )
    consistency_parser.add_argument('--org', type=int, required=True, help='Organization ID')
    consistency_parser.add_argument('--dump-dir', type=Path, default=Path('./output/full_dump'),
                                   help='Dump directory (default: ./output/full_dump)')
    consistency_parser.add_argument('--out-dir', type=Path, default=Path('./output'),
                                   help='Output directory (default: ./output)')
    consistency_parser.add_argument('--min-laps', type=int, default=20, help='Minimum laps to consider (default: 20)')
    consistency_parser.add_argument('--top', type=int, default=10, help='Number of top drivers to show (default: 10)')
    consistency_parser.add_argument('--threshold', type=float, default=0.85, help='Name similarity threshold (default: 0.85)')
    consistency_parser.add_argument('--driver', '--name', dest='driver', help='Specific driver to check percentile for')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'export-full-dump':
            from speedhive_tools.exporters.export_full_dump import main as export_main
            # Convert args to the format expected by the original script
            sys.argv = ['export_full_dump.py',
                       '--org', str(args.org),
                       '--output', str(args.output)]
            if args.verbose:
                sys.argv.append('--verbose')
            if args.no_resume:
                sys.argv.append('--no-resume')
            if args.max_events:
                sys.argv.extend(['--max-events', str(args.max_events)])
            if args.concurrency != 5:
                sys.argv.extend(['--concurrency', str(args.concurrency)])
            return export_main()

        elif args.command == 'process-full-dump':
            from speedhive_tools.processors.process_full_dump import main as process_main
            # Convert args
            sys.argv = ['process_full_dump.py',
                       '--org', str(args.org)]
            if args.dump_dir != Path('./output/full_dump'):
                sys.argv.extend(['--dump-dir', str(args.dump_dir)])
            if args.out_dir != Path('./output'):
                sys.argv.extend(['--out-dir', str(args.out_dir)])
            return process_main()

        elif args.command == 'extract-driver-laps':
            from speedhive_tools.analyzers.driver_laps import main as extract_main
            # Convert args
            sys.argv = ['extract_driver_laps.py',
                       '--org', str(args.org),
                       '--driver', args.driver]
            if args.driver_keys:
                sys.argv.extend(['--driver-keys', args.driver_keys])
            if args.dump_dir != Path('./output/full_dump'):
                sys.argv.extend(['--dump-dir', str(args.dump_dir)])
            if args.out_dir != Path('./output'):
                sys.argv.extend(['--out-dir', str(args.out_dir)])
            if args.threshold != 0.8:
                sys.argv.extend(['--threshold', str(args.threshold)])
            if args.min_laps != 1:
                sys.argv.extend(['--min-laps', str(args.min_laps)])
            return extract_main()

        elif args.command == 'report-consistency':
            from speedhive_tools.analyzers.report_top_bottom_consistency import main as consistency_main
            # Convert args
            sys.argv = ['report_top_bottom_consistency.py',
                       '--org', str(args.org)]
            if args.dump_dir != Path('./output/full_dump'):
                sys.argv.extend(['--dump-dir', str(args.dump_dir)])
            if args.out_dir != Path('./output'):
                sys.argv.extend(['--out-dir', str(args.out_dir)])
            if args.min_laps != 20:
                sys.argv.extend(['--min-laps', str(args.min_laps)])
            if args.top != 10:
                sys.argv.extend(['--top', str(args.top)])
            if args.threshold != 0.85:
                sys.argv.extend(['--threshold', str(args.threshold)])
            if args.driver:
                sys.argv.extend(['--driver', args.driver])
            return consistency_main()

    except ImportError as e:
        print(f"Error importing module: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())