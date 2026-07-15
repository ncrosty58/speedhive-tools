"""Import curated track-record NDJSON into workflow storage."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from speedhive.workflows.track_records.curation import lap_time_to_seconds
from speedhive.stores.track_records import load_curated, paths_for_org, save_curated


_TRACK_RECORD_REQUIRED_FIELDS = ("classAbbreviation", "lapTime", "driverName", "date")
_TRACK_RECORD_OPTIONAL_FIELDS = ("marque", "addedAt")


def _validate_import_line(obj: Dict[str, Any], lineno: int) -> None:
    for field in _TRACK_RECORD_REQUIRED_FIELDS:
        value = obj.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Import aborted: line {lineno} is missing required field '{field}'.")

    if lap_time_to_seconds(obj["lapTime"]) is None:
        raise ValueError(
            f"Import aborted: line {lineno} has unparseable lapTime '{obj['lapTime']}' (want m:ss.mmm or ss.mmm)."
        )

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", obj["date"]):
        raise ValueError(f"Import aborted: line {lineno} has date '{obj['date']}' (want YYYY-MM-DD).")


def import_curated_track_records_ndjson(
    org_id: int,
    track_records_root: Path,
    text: str,
    *,
    replace: bool = False,
) -> str:
    p = paths_for_org(track_records_root, org_id)

    incoming: List[Dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Import aborted: line {lineno} is not valid JSON ({exc.msg}).") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"Import aborted: line {lineno} is not a JSON object.")

        _validate_import_line(obj, lineno)

        record = {field: obj[field].strip() for field in _TRACK_RECORD_REQUIRED_FIELDS}
        for field in _TRACK_RECORD_OPTIONAL_FIELDS:
            if obj.get(field) is not None:
                record[field] = obj[field]
        # Bulk imports should not mark these records as newly approved.
        incoming.append(record)

    if not incoming:
        raise ValueError("File contained no records.")

    curated = load_curated(p)

    def identity(r):
        return (r.get("classAbbreviation"), r.get("lapTime"), r.get("driverName"), r.get("date"))

    if replace:
        curated["records"] = incoming
        notice = f"Replaced curated list with {len(incoming)} imported record(s)."
    else:
        existing = {identity(r) for r in curated.get("records", [])}
        added = [r for r in incoming if identity(r) not in existing]
        curated.setdefault("records", []).extend(added)
        skipped = len(incoming) - len(added)
        notice = f"Imported {len(added)} record(s)" + (f", skipped {skipped} duplicate(s)." if skipped else ".")

    curated["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    save_curated(p, curated)
    return notice
