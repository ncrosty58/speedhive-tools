"""Example: find track records for an organization and stream to a file."""
from __future__ import annotations

import argparse
import json
from speedhive.wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: track records for an org")
    parser.add_argument("--org", type=int, required=True, help="Organization id")
    parser.add_argument("--class", dest="classification", help="Classification filter (optional)")
    parser.add_argument("--output-file", help="File to stream records to (NDJSON format)")
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient.create(token=args.token)

    from speedhive.workflows.track_records.extract import extract_records_from_api

    records = extract_records_from_api(
        client=client,
        org_id=args.org,
        classification=args.classification
    )

    if args.output_file:
        with open(args.output_file, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
            print(f"Finished. Found {len(records)} total records.")
    else:
        for r in records:
            print(r)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
