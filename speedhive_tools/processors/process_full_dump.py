"""
Shim for the removed `process_full_dump` processor.

The heavy processing previously performed by this script has been
migrated to `speedhive_tools.utils.common.compute_laps_and_enriched`.
This module remains as a lightweight shim so older automation that
imports or references `process_full_dump` continues to work and so the
CLI `--help` output remains useful.
"""

from __future__ import annotations

from pathlib import Path
import argparse


def main(argv=None) -> int:  # pragma: no cover - shim
    """Inform users that the processor was removed and how to proceed.

    Returns 2 to indicate non-standard termination when invoked directly.
    """
    print(
        "process_full_dump has been removed. Use `compute_laps_and_enriched` from "
        "`speedhive_tools.utils.common` to compute derived artifacts on-demand."
    )
    return 2


def register_subparser(parser: argparse.ArgumentParser) -> None:
    """Register argparse options for the top-level CLI to show helpful flags."""
    parser.add_argument(
        "--dump-dir", type=Path, default=Path("output/30476"), help="Path to exported dump (output/<org>/)"
    )
    parser.add_argument("--out-dir", type=Path, default=Path("output"), help="Output directory for artifacts")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")


if __name__ == "__main__":
    raise SystemExit(main())
