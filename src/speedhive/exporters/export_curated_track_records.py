"""Export curated track-record workflow data as NDJSON."""
from __future__ import annotations

from pathlib import Path

from speedhive.ndjson import dumps_ndjson
from speedhive.processing.track_records_store import load_curated, paths_for_org


def export_curated_track_records_ndjson(org_id: int, track_records_root: Path) -> str:
    p = paths_for_org(track_records_root, org_id)
    curated = load_curated(p)
    return dumps_ndjson({"records": curated.get("records", [])}, "records")
