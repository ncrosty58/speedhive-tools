
#!/usr/bin/env python3
"""
extract_session_lapdata.py

CLI to fetch lap data for a specific session and finishing position, and
output as JSON (default) or CSV. Uses SpeedHiveClient.

Usage examples:
  python extract_session_lapdata.py --session-id 10998445 --position 3
  python extract_session_lapdata.py --session-id 10998445 --position 3 --format csv --out laps_10998445_p3.csv
  python extract_session_lapdata.py --session-id 10998445 --position 3 --out laps_10998445_p3.json

Environment:
  SPEEDHIVE_API_KEY  (optional)
  SPEEDHIVE_BASE_URL (optional; defaults to Event Results base)
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

from speedhive_tools.client import SpeedHiveClient, DEFAULT_BASE_URL


def write_json(rows: List[Dict[str, Any]], path: str | None) -> None:
    if not path:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(rows: List[Dict[str, Any]], path: str | None) -> None:
    if not rows:
        hdr: List[str] = []
    else:
        hdr = sorted({k for r in rows for k in r.keys()})
    if not path:
        w = csv.DictWriter(sys.stdout, fieldnames=hdr)
        if hdr:
            w.writeheader()
        for r in rows:
            w.writerow(r)
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr)
        if hdr:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="extract_session_lapdata.py",
        description="Fetch lap data for a Speedhive session and finishing position",
    )
    p.add_argument("--session-id", type=int, required=True, help="Session ID (e.g., 10998445)")
    p.add_argument("--position", type=int, default=1, help="Finishing position (e.g., 3 for P3)")
    p.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    p.add_argument("--out", type=str, default=None, help="Optional output path; prints to stdout if omitted")
    p.add_argument("--base-url", type=str, default=os.getenv("SPEEDHIVE_BASE_URL", DEFAULT_BASE_URL), help="Override base URL")
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--retries", type=int, default=2)
    return p


def main(argv: List[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    api_key = os.getenv("SPEEDHIVE_API_KEY", None)
    client = SpeedHiveClient(api_key=api_key, base_url=args.base_url, timeout=args.timeout, retries=args.retries)

    rows = client.get_session_lap_data(args.session_id, args.position)
    # Enrich each row with session and position for helpful downstream joins
    enriched = []
    for r in rows:
        if isinstance(r, dict):
            r = dict(r)
            r.setdefault("sessionId", args.session_id)
            r.setdefault("position", args.position)
        enriched.append(r)

    if args.format == "json":
        write_json(enriched, args.out)
    else:
        write_csv(enriched, args.out)


if __name__ == "__main__":
    main()
