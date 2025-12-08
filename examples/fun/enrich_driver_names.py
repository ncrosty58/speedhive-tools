#!/usr/bin/env python3
"""Enrich anonymous driver IDs using session results.

This utility finds driver IDs of the form `session{session_id}_pos{position}`
and fetches the session results (classification) for the referenced session to
map the position to a competitor name. It performs only the minimal number of
API calls required (one per affected session), so it is fast compared to
re-downloading all laps.

Usage:
  # Provide a stats JSON produced by consistency_by_driver.py --out
  PYTHONPATH=. python examples/fun/enrich_driver_names.py --stats output/consistency_30476.json --token $TOKEN --out-enriched output/consistency_30476_enriched.json

If you used `--save-laps` previously and created `output/laps_by_driver_<org>.json`,
you can also point `--laps-file` to that file; the script will infer anonymous
driver IDs from its keys.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

# allow importing wrapper
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from mylaps_client_wrapper import SpeedhiveClient


SESSION_ID_RE = re.compile(r"^session(?P<session_id>\d+)_pos(?P<pos>\d+)$")


def load_stats(path: Path) -> Dict:
    j = json.loads(path.read_text(encoding="utf8"))
    # Accept either full structure or just stats_by_driver
    if "stats_by_driver" in j:
        return j["stats_by_driver"]
    return j


def load_laps_file(path: Path) -> Dict[str, List[float]]:
    return json.loads(path.read_text(encoding="utf8"))


def enrich(names_by_driver: Dict[str, Dict], client: SpeedhiveClient) -> Dict[str, Dict]:
    """For any driver keys matching session{session_id}_pos{pos}, fetch session results and fill name."""
    # Collect sessions to fetch
    sessions_needed: Dict[str, List[str]] = {}
    for driver_id in list(names_by_driver.keys()):
        m = SESSION_ID_RE.match(driver_id)
        if m:
            sid = m.group("session_id")
            sessions_needed.setdefault(sid, []).append(driver_id)

    for sid, driver_keys in sessions_needed.items():
        try:
            results = client.get_results(session_id=int(sid))
        except Exception:
            results = []
        # Build mapping position -> name
        pos_name = {}
        for r in results:
            pos = r.get("position") or r.get("pos")
            comp = r.get("competitor") or {}
            name = r.get("name") or comp.get("name") or r.get("participantName")
            if pos is not None and name:
                pos_name[int(pos)] = name

        for dk in driver_keys:
            m = SESSION_ID_RE.match(dk)
            if not m:
                continue
            pos = int(m.group("pos"))
            if pos in pos_name:
                # Overwrite name field
                names_by_driver[dk]["name"] = pos_name[pos]

    return names_by_driver


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Enrich anonymous driver IDs by fetching session results")
    parser.add_argument("--stats", type=Path, help="Path to stats JSON produced by consistency_by_driver.py (optional if --laps-file provided)")
    parser.add_argument("--laps-file", type=Path, help="Optional laps_by_driver JSON file saved with --save-laps")
    parser.add_argument("--token", help="API token if required")
    parser.add_argument("--out-enriched", type=Path, default=Path("output/enriched_stats.json"), help="Output path for enriched stats JSON")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)

    driver_stats = {}
    if args.stats and args.stats.exists():
        driver_stats = load_stats(args.stats)
    elif args.laps_file and args.laps_file.exists():
        # construct minimal stats structure from laps keys
        laps = load_laps_file(args.laps_file)
        for k, v in laps.items():
            driver_stats[k] = {"name": None, "driver_id": k, "lap_count": len(v)}
    else:
        print("Provide either --stats or --laps-file pointing to saved data.")
        return 2

    # Convert to mutable mapping driver_id -> dict
    for k in list(driver_stats.keys()):
        if not isinstance(driver_stats[k], dict):
            driver_stats[k] = {"name": driver_stats[k]}

    enriched = enrich(driver_stats, client)

    args.out_enriched.parent.mkdir(parents=True, exist_ok=True)
    args.out_enriched.write_text(json.dumps(enriched, indent=2), encoding="utf8")
    print(f"Wrote enriched stats to {args.out_enriched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
