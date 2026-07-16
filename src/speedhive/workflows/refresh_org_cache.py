"""Refresh organization data into the primary SQLite cache."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from speedhive.storage import SpeedhiveStorage
from speedhive.wrapper import SpeedhiveClient


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_db_path() -> Path:
    db_path = os.environ.get("SPEEDHIVE_DB_PATH")
    if db_path:
        return Path(db_path)
    data_dir = os.environ.get("SPEEDHIVE_DATA_DIR", "./data")
    return Path(data_dir) / "speedhive.db"


def _parse_iso_utc(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


def _event_datetime_value(event: Dict[str, Any]) -> Optional[str]:
    for key in ("startTime", "startDate", "startDateTime", "scheduledStart", "date", "start", "eventDate", "event_date"):
        value = event.get(key)
        if value:
            return str(value)
    return None


def _event_sort_key(event: Dict[str, Any]) -> tuple[str, int]:
    dt = _event_datetime_value(event) or ""
    event_id = _safe_int(event.get("id")) or 0
    return (dt, event_id)


def _event_ids_from_rows(rows: Sequence[Dict[str, Any]]) -> List[int]:
    ids: List[int] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        eid = _safe_int(row.get("id"))
        if eid is not None:
            ids.append(eid)
    return ids

def _sorted_event_ids_for_backfill(events: Sequence[Dict[str, Any]], count: int) -> List[int]:
    if count <= 0:
        return []
    sortable = [row for row in events if isinstance(row, dict) and _safe_int(row.get("id")) is not None]
    sortable.sort(key=_event_sort_key, reverse=True)
    return [_safe_int(row.get("id")) for row in sortable[:count] if _safe_int(row.get("id")) is not None]


def refresh_org_cache(
    client: SpeedhiveClient,
    org_id: int,
    mode: str = "incremental",
    *,
    max_events: Optional[int] = None,
    recent_backfill_events: int = 0,
    cleanup_on_full: bool = True,
    storage: SpeedhiveStorage,
) -> Dict[str, Any]:
    """Refresh cache for one organization.

    Modes:
    - `full`: refresh all current events/sessions and optionally clean old cache directories.
    - `incremental`: refresh only new events not seen before (+ optional recent-event backfill).
    """
    mode = (mode or "incremental").strip().lower()
    if mode not in {"full", "incremental"}:
        raise ValueError("mode must be 'full' or 'incremental'")

    previous_state = storage.get_refresh_state(org_id).payload
    if not isinstance(previous_state, dict):
        previous_state = {}

    previous_event_rows = storage.get_events(org_id).payload or []
    previous_event_ids = {
        _safe_int(event.get("id"))
        for event in previous_event_rows
        if isinstance(event, dict) and _safe_int(event.get("id")) is not None
    }
    previous_session_ids = {
        _safe_int(session_id)
        for session_id in storage.load_session_payloads(org_id).keys()
        if _safe_int(session_id) is not None
    }
    prev_full_at = previous_state.get("last_full_refresh_at")
    prev_incremental_at = previous_state.get("last_incremental_refresh_at")

    organization = client.get_organization(org_id) or {"id": org_id, "name": f"Organization #{org_id}"}
    championships = client.get_championships(org_id) or []
    events = list(client.iter_events(org_id))
    if max_events is not None:
        events = events[:max(0, int(max_events))]

    refresh_saved_at = _utc_now_iso()
    with storage.connect() as conn:
        storage.save_organization(org_id, organization, saved_at=refresh_saved_at, conn=conn)
        storage.save_championships(org_id, championships, saved_at=refresh_saved_at, conn=conn)
        storage.save_events(org_id, events, saved_at=refresh_saved_at, conn=conn)

    current_event_ids = _event_ids_from_rows(events)
    current_event_id_set = set(current_event_ids)
    new_event_ids = sorted(current_event_id_set - previous_event_ids)

    refresh_event_ids: Set[int]
    if mode == "full":
        refresh_event_ids = set(current_event_id_set)
    else:
        refresh_event_ids = set(new_event_ids)
        refresh_event_ids.update(_sorted_event_ids_for_backfill(events, recent_backfill_events))

    refreshed_events = 0
    refreshed_sessions = 0
    known_session_ids: Set[int] = set() if mode == "full" else set(previous_session_ids)

    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = _safe_int(event.get("id"))
        if event_id is None:
            continue
        if event_id not in refresh_event_ids:
            continue

        event_detail = client.get_event(event_id, include_sessions=True) or {}
        sessions = client.get_sessions(event_id) or []
        with storage.connect() as conn:
            storage.save_event(event_id, org_id, event_detail, saved_at=refresh_saved_at, conn=conn)
            storage.save_event_sessions(event_id, org_id, sessions, saved_at=refresh_saved_at, conn=conn)
        refreshed_events += 1

        for session in sessions:
            if not isinstance(session, dict):
                continue
            sid = _safe_int(session.get("id"))
            if sid is None:
                continue

            session_detail = client.get_session(sid) or {}
            results = client.get_results(sid) or []
            laps = client.get_laps(sid) or []
            announcements = client.get_announcements(sid) or []
            lap_chart = client.get_lap_chart(sid) or []
            with storage.connect() as conn:
                storage.save_session(sid, event_id, org_id, session_detail, saved_at=refresh_saved_at, conn=conn)
                storage.save_results(sid, event_id, org_id, results, saved_at=refresh_saved_at, conn=conn)
                storage.save_laps(sid, event_id, org_id, laps, saved_at=refresh_saved_at, conn=conn)
                storage.save_announcements(sid, event_id, org_id, announcements, saved_at=refresh_saved_at, conn=conn)
                storage.save_lap_chart(sid, event_id, org_id, lap_chart, saved_at=refresh_saved_at, conn=conn)

            known_session_ids.add(sid)
            refreshed_sessions += 1

    removed_event_dirs = 0
    removed_session_dirs = 0
    if mode == "full" and cleanup_on_full:
        storage_removed_events, storage_removed_sessions = storage.prune_org(org_id, current_event_id_set, known_session_ids)
        removed_event_dirs += storage_removed_events
        removed_session_dirs += storage_removed_sessions

    refreshed_at = _utc_now_iso()
    full_at = refreshed_at if mode == "full" else prev_full_at
    incremental_at = refreshed_at if mode == "incremental" else prev_incremental_at
    refresh_dt_candidates = [dt for dt in (_parse_iso_utc(full_at), _parse_iso_utc(incremental_at)) if dt]
    last_refresh_at = (
        max(refresh_dt_candidates).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if refresh_dt_candidates
        else refreshed_at
    )

    refresh_state = {
        "org_id": org_id,
        "last_refresh_at": last_refresh_at,
        "last_refresh_mode": mode,
        "last_full_refresh_at": full_at,
        "last_incremental_refresh_at": incremental_at,
        "events_cached": len(current_event_id_set),
        "sessions_cached": len(known_session_ids),
        "championships_cached": len(championships),
        "cached_event_ids": sorted(current_event_id_set),
        "cached_session_ids": sorted(known_session_ids),
        "new_events_detected": len(new_event_ids),
        "backfill_events_requested": int(max(0, recent_backfill_events)),
        "refreshed_events": refreshed_events,
        "refreshed_sessions": refreshed_sessions,
        "removed_event_dirs": removed_event_dirs,
        "removed_session_dirs": removed_session_dirs,
    }
    storage.save_refresh_state(org_id, refresh_state, saved_at=refresh_saved_at)
    return refresh_state


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh Speedhive organization data into the primary SQLite cache")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    parser.add_argument("--mode", choices=["full", "incremental"], default="incremental")
    parser.add_argument("--max-events", type=int, default=None, help="Optional event cap")
    parser.add_argument(
        "--recent-backfill-events",
        type=int,
        default=0,
        help="Also refresh the most recent N events during incremental mode",
    )
    parser.add_argument("--token", default=None, help="API token")
    args = parser.parse_args(argv)

    client = SpeedhiveClient.create(token=args.token)
    storage = SpeedhiveStorage(args.db_path)
    summary = refresh_org_cache(
        client=client,
        org_id=args.org,
        mode=args.mode,
        max_events=args.max_events,
        recent_backfill_events=args.recent_backfill_events,
        storage=storage,
    )
    print(
        json.dumps(
            {
                "org_id": summary.get("org_id"),
                "mode": summary.get("last_refresh_mode"),
                "last_refresh_at": summary.get("last_refresh_at"),
                "events_cached": summary.get("events_cached"),
                "sessions_cached": summary.get("sessions_cached"),
                "refreshed_events": summary.get("refreshed_events"),
                "refreshed_sessions": summary.get("refreshed_sessions"),
                "new_events_detected": summary.get("new_events_detected"),
            },
            ensure_ascii=False,
        )
    )
    return 0


def register_subparser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    parser.add_argument("--mode", choices=["full", "incremental"], default="incremental")
    parser.add_argument("--max-events", type=int, default=None, help="Optional event cap")
    parser.add_argument("--recent-backfill-events", type=int, default=0)
    parser.add_argument("--token", default=None, help="API token")
