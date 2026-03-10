"""Example: find track records for an organization and stream to a file."""
from __future__ import annotations

import argparse
import json
from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: track records for an org")
    parser.add_argument("--org", type=int, required=True, help="Organization id")
    parser.add_argument("--class", dest="classification", help="Classification filter (optional)")
    parser.add_argument("--output-file", help="File to stream records to (NDJSON format)")
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    
    record_iterator = client.iter_track_records_by_event(
        org_id=args.org,
        classification=args.classification
    )

    if args.output_file:
        with open(args.output_file, "w") as f:
            count = 0
            for record in record_iterator:
                f.write(json.dumps(record) + "\n")
                count += 1
                if count % 10 == 0:
                    print(f"Found {count} records...", end="\r")
            print(f"Finished. Found {count} total records.")
    else:
        for r in record_iterator:
            print(r)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
