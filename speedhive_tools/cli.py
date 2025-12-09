#!/usr/bin/env python3
"""Speedhive Tools CLI - Unified command-line interface for Speedhive data tools."""

import argparse
import sys
from pathlib import Path
import importlib
import pkgutil
import shlex


def _ask(prompt, default=None, required=False, cast=str):
    """Simple interactive prompt helper used by the CLI interactive menu."""
    try:
        prompt_str = f"{prompt}"
        if default is not None and default != "":
            prompt_str += f" [{default}]"
        prompt_str += ": "
        val = input(prompt_str)
    except (EOFError, KeyboardInterrupt):
        return None

    if val == "" and default is not None:
        val = default

    if required and (val is None or val == ""):
        print("Value required")
        return _ask(prompt, default=default, required=required, cast=cast)

    if val == "":
        return val

    try:
        return cast(val)
    except Exception:
        print("Invalid value")
        return _ask(prompt, default=default, required=required, cast=cast)


def _discover_modules():
    """Discover exporter/processor/analyzer modules under the package.

    Returns a list of tuples: (command_name, module_object, category)
    where `command_name` is the hyphenated name used on the CLI.
    """
    found = []
    for pkg_name, category in (
        ("speedhive_tools.exporters", "exporters"),
        ("speedhive_tools.processors", "processors"),
        ("speedhive_tools.analyzers", "analyzers"),
    ):
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception:
            continue

        if not hasattr(pkg, "__path__"):
            continue

        for finder, name, ispkg in pkgutil.iter_modules(pkg.__path__):
            full_name = f"{pkg_name}.{name}"
            try:
                mod = importlib.import_module(full_name)
            except Exception:
                # skip modules that fail to import at discovery time
                continue

            # treat presence of a callable `main` as indicating a runnable command
            if hasattr(mod, "main") and callable(getattr(mod, "main")):
                cmd = name.replace("_", "-")
                found.append((cmd, mod, category))

    return found

def main():
    parser = argparse.ArgumentParser(
        description="Speedhive Tools - Utilities for MyLaps Event Results API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
            speedhive export-full-dump --org 30476 --output ./output
    """
    )
    # register subparsers (discovered modules only)
    subparsers = parser.add_subparsers(dest="command")

    # Auto-register discovered modules: prefer module-provided `register_subparser`
    for cmd, mod, cat in _discover_modules():
        try:
            sp = subparsers.add_parser(cmd, help=f"{cat} ({cmd})")
            if hasattr(mod, "register_subparser") and callable(getattr(mod, "register_subparser")):
                try:
                    mod.register_subparser(sp)
                    sp.set_defaults(_speedhive_module=mod, _speedhive_cmd=cmd)
                except Exception:
                    # fallback to passthrough if registration fails
                    sp.add_argument("extra_args", nargs=argparse.REMAINDER)
                    sp.set_defaults(_speedhive_module=mod, _speedhive_cmd=cmd)
            else:
                sp.add_argument("extra_args", nargs=argparse.REMAINDER)
                sp.set_defaults(_speedhive_module=mod, _speedhive_cmd=cmd)
        except Exception:
            # ignore discovery/registration errors
            continue

    args = parser.parse_args()

    # If a discovered module was registered, dispatch to it directly
    mod = getattr(args, "_speedhive_module", None)
    if mod is not None:
        extra = getattr(args, "extra_args", None)
        try:
            # Many module mains accept an argv list; pass extra when present
            return mod.main(argv=extra if extra is not None else None)
        except SystemExit:
            return 0

    print("Speedhive Tools - Interactive Mode")
    while True:
        discovered = _discover_modules()
        cats = {'exporters': [], 'processors': [], 'analyzers': []}
        for cmd, mod, cat in discovered:
            cats.setdefault(cat, []).append((cmd, mod))

        print("\nDiscovered commands:\n")
        idx = 1
        idx_map = {}
        for cat in ('exporters', 'processors', 'analyzers'):
            items = cats.get(cat, [])
            if not items:
                continue
            print(f"{cat.title()}: ")
            for cmd, mod in items:
                print(f" {idx}) {cmd}")
                idx_map[idx] = (cmd, mod)
                idx += 1
            print("")

        print(f" {idx}) Exit")

        choice = _ask("Enter choice", default=str(idx))
        if choice is None:
            continue
        try:
            choice_i = int(choice)
        except Exception:
            print("Please enter a valid number.")
            continue

        if choice_i == idx:
            print("Goodbye.")
            return 0

        if choice_i not in idx_map:
            print("Invalid choice")
            continue

        cmd, module = idx_map[choice_i]
        extra = _ask("Extra args (e.g. --org 30476)", default="", cast=str)
        argv_list = shlex.split(extra) if extra else []

    # Convenience: if user supplied --org but not --dump-dir and an export exists,
    # prefer using `output/<org>` as the dump directory so analyzers/processors
    # operate on the exported dump by default.
        try:
            if "--org" in argv_list and "--dump-dir" not in argv_list:
                # find the org value following --org
                try:
                    i = argv_list.index("--org")
                    org_val = argv_list[i + 1]
                except Exception:
                    org_val = None
                if org_val:
                    candidate = Path("output") / str(org_val)
                    if candidate.exists():
                        argv_list.extend(["--dump-dir", str(Path("output"))])

            # prefer modules that accept argv parameter
            try:
                module.main(argv=argv_list if argv_list else None)
            except TypeError:
                # fallback: set sys.argv and call main()
                sys_argv = [f"{cmd}.py"] + (argv_list if argv_list else [])
                sys.argv = sys_argv
                module.main()
        except SystemExit:
            pass

    # If no subcommand was provided, run interactive menu
    if not args.command:
        return interactive_menu()

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

        # 'process-full-dump' was removed; processing is available on-demand via
        # `speedhive_tools.utils.common.compute_laps_and_enriched` and individual
        # processors/analyzers will compute artifacts when needed.

        elif args.command == 'extract-driver-laps':
            from speedhive_tools.analyzers.driver_laps import main as extract_main
            # Convert args
            sys.argv = ['extract_driver_laps.py',
                       '--org', str(args.org),
                       '--driver', args.driver]
            if args.driver_keys:
                sys.argv.extend(['--driver-keys', args.driver_keys])
            if args.dump_dir != Path('./output'):
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
            if args.dump_dir != Path('./output'):
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