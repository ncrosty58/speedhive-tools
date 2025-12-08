#!/usr/bin/env python3
"""Find the most and least consistent drivers by lap time.

This script uses only the `SpeedhiveClient` wrapper to download laps for
an organization, groups lap times by driver, and computes statistics to
rank drivers by consistency.

Statistics used (per driver):
- N: number of laps considered (we filter drivers with fewer than `--min-laps`)
- mean: arithmetic mean of lap times (seconds)
- median: median lap time (seconds)
- stddev: sample standard deviation of lap times (seconds)
- cv (coefficient of variation): stddev / mean (unitless) — primary consistency metric
- mad: median absolute deviation (robust dispersion measure)

We rank drivers by `cv` (lower = more consistent). For robustness we also
report `mad` and `stddev` so you can inspect differences.

Usage:
  python examples/fun/consistency_by_driver.py --org 30476 --token $TOKEN

Notes:
- This script iterates events -> sessions -> laps. It maps competitor IDs
  to driver names using the session results/classification when available.
- The script is conservative with network usage but will download all laps
  for the given organization. Use `--limit-events` to restrict scanning.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mylaps_client_wrapper import SpeedhiveClient


def median_absolute_deviation(values: List[float]) -> float:
    """Compute the median absolute deviation (MAD).

    This returns the unscaled MAD (median(|xi - median(x)|)). For Gaussian
    equivalence multiply by ~1.4826; we report the raw MAD here as a robust
    dispersion measure.
    """
    if not values:
        return float("nan")
    med = statistics.median(values)
    deviations = [abs(x - med) for x in values]
    return statistics.median(deviations)


def summarize_driver(lap_seconds: List[float]) -> Dict[str, Optional[float]]:
    n = len(lap_seconds)
    if n == 0:
        return {}
    mean = statistics.mean(lap_seconds)
    median = statistics.median(lap_seconds)
    stddev = statistics.pstdev(lap_seconds) if n == 1 else statistics.stdev(lap_seconds)
    cv = stddev / mean if mean and not math.isclose(mean, 0.0) else float("inf")
    mad = median_absolute_deviation(lap_seconds)
    return {
        "n": n,
        "mean": mean,
        "median": median,
        "stddev": stddev,
        "cv": cv,
        "mad": mad,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compute lap-time consistency per driver for an org")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--token", help="API token (if required)")
    parser.add_argument("--min-laps", type=int, default=5, help="Minimum laps to include driver (default: 5)")
    parser.add_argument("--top", type=int, default=3, help="How many top results to show (default: 3)")
    parser.add_argument("--limit-events", type=int, help="Limit number of events to scan (for testing)")
    parser.add_argument("--out", help="Optional JSON output file to write full driver stats")
    parser.add_argument("--save-laps", dest="save_laps", action="store_true", help="Save downloaded laps to output/laps_by_driver_<org>.json for reuse")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)

    print(f"Scanning organization {args.org} for events/sessions/laps...", file=sys.stderr)

    # driver_id -> list of lap times in seconds
    laps_by_driver: Dict[str, List[float]] = defaultdict(list)
    # driver_id -> human name (when available)
    name_by_driver: Dict[str, str] = {}

    # Iterate events and sessions
    events = client.get_events(org_id=args.org, limit=args.limit_events or 10000)
    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue
        try:
            sessions = client.get_sessions(event_id=event_id)
        except Exception:
            continue

        for session in sessions:
            session_id = session.get("id")
            if not session_id:
                continue

            # Build competitorId -> name mapping from results when possible
            try:
                results = client.get_results(session_id=session_id)
            except Exception:
                results = []
            for r in results:
                comp = r.get("competitor") or {}
                comp_id = r.get("competitorId") or r.get("competitor_id") or comp.get("id")
                name = r.get("name") or comp.get("name") or r.get("participantName")
                if comp_id and name:
                    name_by_driver[str(comp_id)] = name

            # Fetch laps for session (flattened)
            try:
                laps = client.get_laps(session_id=session_id, flatten=True)
            except Exception:
                laps = []

            for lap in laps:
                comp_id = lap.get("competitorId") or lap.get("competitor_id") or lap.get("id")
                # lap time may be string like "1:03.004" or numeric
                lap_time_raw = lap.get("lapTime") or lap.get("lap_time") or lap.get("time")
                if lap_time_raw is None:
                    continue
                # Parse to seconds: reuse wrapper parser if available
                try:
                    # call static helper on SpeedhiveClient
                    seconds = SpeedhiveClient._parse_lap_time(lap_time_raw if isinstance(lap_time_raw, str) else str(lap_time_raw))
                except Exception:
                    seconds = None
                if seconds is None:
                    continue
                if comp_id is None:
                    # anonymous competitor; use session+position as fallback
                    comp_id = f"session{session_id}_pos{lap.get('position') or 'x'}"
                comp_key = str(comp_id)
                laps_by_driver[comp_key].append(seconds)

    # Compute stats per driver
    stats_by_driver: Dict[str, Dict] = {}
    for driver_id, lap_list in laps_by_driver.items():
        if len(lap_list) < args.min_laps:
            continue
        stats = summarize_driver(lap_list)
        stats_by_driver[driver_id] = {
            "name": name_by_driver.get(driver_id),
            "driver_id": driver_id,
            "lap_count": stats.get("n"),
            "mean": stats.get("mean"),
            "median": stats.get("median"),
            "stddev": stats.get("stddev"),
            "cv": stats.get("cv"),
            "mad": stats.get("mad"),
        }

    if not stats_by_driver:
        print("No drivers with sufficient laps found.")
        return 1

    # Rank by CV (coefficient of variation)
    sorted_by_cv = sorted(stats_by_driver.values(), key=lambda d: (d["cv"] if d["cv"] is not None else float("inf")))

    top_n = args.top

    most_consistent = sorted_by_cv[:top_n]
    least_consistent = list(reversed(sorted_by_cv))[:top_n]

    # Print explanation of metrics
    print("\nStatistical methods used:")
    print("- mean: arithmetic average of lap times (seconds)")
    print("- stddev: sample standard deviation of lap times (seconds)")
    print("- cv: coefficient of variation = stddev / mean (lower => more consistent)")
    print("- median: median lap time (seconds)")
    print("- mad: median absolute deviation (robust dispersion)")

    def print_block(title: str, rows: List[Dict]):
        print(f"\n{title}")
        print("-" * 80)
        for r in rows:
            name = r.get("name") or "<unknown>"
            print(f"Name: {name}")
            print(f"  Driver ID : {r['driver_id']}")
            print(f"  Laps      : {r['lap_count']}")
            print(f"  Mean (s)  : {r['mean']:.3f}")
            print(f"  Median(s) : {r['median']:.3f}")
            print(f"  Stddev(s) : {r['stddev']:.3f}")
            print(f"  CV        : {r['cv']:.6f}")
            print(f"  MAD(s)    : {r['mad']:.3f}")
            print("  Math/Notes: CV = stddev/mean; MAD = median(|xi - median|)")
            print()

    print_block(f"Top {top_n} Most Consistent Drivers (by CV)", most_consistent)
    print_block(f"Top {top_n} Least Consistent Drivers (by CV)", least_consistent)

    # Optionally save raw laps for reuse (so future runs don't need to re-download)
    if args.save_laps:
        out_dir = Path("output")
        out_dir.mkdir(parents=True, exist_ok=True)
        laps_out = out_dir / f"laps_by_driver_{args.org}.json"
        # Save compact JSON mapping driver_id -> list of lap seconds
        compact = {d: laps_by_driver[d] for d in laps_by_driver}
        laps_out.write_text(json.dumps(compact, indent=2), encoding="utf8")
        print(f"Saved raw laps to {laps_out}")

    # Optionally write JSON output with stats
    if args.out:
        out_path = Path(args.out)
        out_path.write_text(json.dumps({"stats_by_driver": stats_by_driver, "most_consistent": most_consistent, "least_consistent": least_consistent}, indent=2), encoding="utf8")
        print(f"Wrote full stats to {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
