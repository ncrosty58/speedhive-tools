
# speedhive_example_runner.py
# No CLI arguments. Just run:
#   python speedhive_example_runner.py
#
# This demonstrates:
#   1) Export by organization ID (30476 for Waterford Hills) -> waterford_hills_by_id.json
#   2) Export by name ("Waterford Hills") -> waterford_hills_by_name.json
#
# Output:
# { "records": [ { "classAbbreviation": "...", "lapTime": "...", "driverName": "...", "marque": "...", "date": "YYYY-MM-DD" }, ... ] }

from speedhive_client import SpeedHiveClient, SpeedHiveError


def run_by_org():
    org_id = 30476  # Waterford Hills
    out_path = "waterford_hills_by_id.json"

    print(f"Searching by organization ID {org_id}...")
    client = SpeedHiveClient()

    try:
        org = client.get_organization_by_id(org_id)
        print(f"  Found organization: {org.get('name')} (id={org.get('id')})")
    except SpeedHiveError as e:
        print(f"[error] Could not fetch organization {org_id}: {e}")
        return

    try:
        result = client.export_all_track_records_for_organization(org_id, out_path)
        print(f"[ok] Wrote {len(result.get('records', []))} 'New Track Record' rows to: {out_path}")
    except SpeedHiveError as e:
        print(f"[error] Export failed for org {org_id}: {e}")


def run_by_name():
    name = "Waterford Hills"
    out_path = "waterford_hills_by_name.json"

    print(f"Searching by organization name {name!r}...")
    client = SpeedHiveClient()

    try:
        result = client.export_all_track_records_for_organization_name(name, out_path)
        print(f"[ok] Wrote {len(result.get('records', []))} 'New Track Record' rows to: {out_path}")
    except SpeedHiveError as e:
        print(f"[error] Name-based export failed: {e}")


def main():
    run_by_org()
    print("-" * 60)
    #run_by_name()


if __name__ == "__main__":
    main()
