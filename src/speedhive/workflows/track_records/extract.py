"""Extract track-record announcements from SQLite database."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from speedhive.analysis.lap_analysis import extract_iso_date, parse_track_record_text
from speedhive.storage import SpeedhiveStorage

def extract_records_from_storage(org: int, db_path: Path, classification: str | None = None) -> List[Dict[str, Any]]:
    storage = SpeedhiveStorage(db_path)
    if not storage.org_has_sessions(org):
        return []

    session_map = storage.load_session_payloads(org)
    event_map = storage.load_event_payloads(org)
    announcements_map = storage.load_announcements_payloads(org)

    records: List[Dict[str, Any]] = []
    wanted_class = classification.upper() if classification else None

    for session_id, announcements in announcements_map.items():
        session_raw = session_map.get(session_id, {})
        event_id = (
            session_raw.get("event_id")
            or session_raw.get("eventId")
            or (session_raw.get("event") or {}).get("id")
        )
        event_key = str(int(event_id)) if event_id not in (None, "") else None
        event_raw = event_map.get(event_key or "", {})
        event_name = (
            (event_raw or {}).get("name")
            or (session_raw.get("event") or {}).get("name")
            or session_raw.get("event_name")
            or session_raw.get("eventName")
        )
        session_name = session_raw.get("name") or session_raw.get("sessionName")

        for announcement in announcements:
            if not isinstance(announcement, dict):
                continue
            text = announcement.get("text") or announcement.get("message") or ""
            parsed = parse_track_record_text(text)
            if not parsed:
                continue
            class_name = (parsed.get("classification") or "Unknown").upper()
            if wanted_class and class_name != wanted_class:
                continue
            timestamp = (
                announcement.get("timestamp")
                or announcement.get("time")
                or extract_iso_date(session_raw)
                or extract_iso_date(event_raw)
            )
            records.append(
                {
                    "event_id": int(event_id) if event_id not in (None, "") else None,
                    "event_name": event_name,
                    "session_id": int(session_id),
                    "session_name": session_name,
                    "classification": parsed.get("classification"),
                    "lap_time": parsed.get("lap_time"),
                    "lap_time_seconds": parsed.get("lap_time_seconds"),
                    "driver": parsed.get("driver"),
                    "marque": parsed.get("marque"),
                    "timestamp": timestamp,
                    "text": text,
                }
            )

    records.sort(key=lambda row: ((row.get("classification") or "").upper(), row.get("lap_time_seconds") or float("inf")))
    return records
