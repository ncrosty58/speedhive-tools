"""Export track-record announcements from the primary SQLite cache to NDJSON."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from speedhive.ndjson import dumps_ndjson
from speedhive.storage import SpeedhiveStorage


def default_db_path() -> Path:
    return Path(os.environ.get("SPEEDHIVE_DB_PATH", "./web_data/speedhive.db"))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export track records from the primary SQLite cache to NDJSON")
    parser.add_argument("--org", type=int, required=True)
    parser.add_argument("--classification", default=None)
    parser.add_argument("--db-path", type=Path, default=default_db_path())
    parser.add_argument("--output", default=None, help="Output file path (NDJSON)")
    args = parser.parse_args(argv)

    if not args.db_path.exists():
        print(f"Error: Database file does not exist at '{args.db_path}'. Please sync or import first.", file=sys.stderr)
        return 1

    storage = SpeedhiveStorage(args.db_path)
    records = storage.get_track_records(args.org, args.classification)

    body = dumps_ndjson(
        {
            "org_id": args.org,
            "classification": args.classification,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "records": records,
        },
        "records",
    )
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(body, encoding="utf8")
        print(f"Wrote {out_path} ({len(records)} records)")
    else:
        sys.stdout.write(body)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
