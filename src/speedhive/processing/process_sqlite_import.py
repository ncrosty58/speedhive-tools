"""Import offline NDJSON(.gz) dumps into the primary SQLite cache."""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List

from speedhive.processing.process_lap_analysis import load_session_map, parse_track_record_text
from speedhive.processing.ndjson import open_ndjson
from speedhive.storage import SpeedhiveStorage


def default_db_path() -> Path:
    return Path(os.environ.get("SPEEDHIVE_DB_PATH", "./web_data/speedhive.db"))


def _prefer_gz(path: Path) -> Path:
    gz_path = path.with_suffix(path.suffix + ".gz")
    if gz_path.exists():
        return gz_path
    return path


def import_dump_to_storage(org: int, dump_dir: Path, db_path: Path) -> Dict[str, int]:
    dump = dump_dir / str(org)
    if not dump.exists():
        raise FileNotFoundError(f"Dump directory for organization {org} does not exist at: {dump}")

    storage = SpeedhiveStorage(db_path)
    summary = {
        "events": 0,
        "sessions": 0,
        "results": 0,
        "laps": 0,
        "announcements": 0,
    }

    events_path = _prefer_gz(dump / "events.ndjson")
    sessions_path = _prefer_gz(dump / "sessions.ndjson")
    results_path = _prefer_gz(dump / "results.ndjson")
    laps_path = _prefer_gz(dump / "laps.ndjson")
    announcements_path = _prefer_gz(dump / "announcements.ndjson")

    org_name = None
    events_payload: List[Dict[str, Any]] = []
    event_payloads: Dict[int, Dict[str, Any]] = {}
    event_sessions: Dict[int, List[Dict[str, Any]]] = {}
    sessions_payloads: Dict[int, Dict[str, Any]] = {}
    results_payloads: Dict[int, List[Dict[str, Any]]] = {}
    laps_payloads: Dict[int, List[Dict[str, Any]]] = {}
    announcements_payloads: Dict[int, List[Dict[str, Any]]] = {}

    if events_path.exists():
        for entry in open_ndjson(events_path):
            raw = entry.get("raw") if isinstance(entry, dict) else None
            event = raw if isinstance(raw, dict) else entry
            if not isinstance(event, dict):
                continue
            event_id = event.get("id") or entry.get("event_id") or entry.get("eventId")
            try:
                event_id = int(event_id)
            except Exception:
                continue
            event = dict(event)
            event.setdefault("id", event_id)
            event.setdefault("organizationId", org)
            org_name = org_name or ((event.get("organization") or {}).get("name")) or entry.get("organizationName")
            events_payload.append(event)
            event_payloads[event_id] = event
        summary["events"] = len(events_payload)

    if sessions_path.exists():
        for entry in open_ndjson(sessions_path):
            raw = entry.get("raw") if isinstance(entry, dict) else None
            session = raw if isinstance(raw, dict) else entry
            if not isinstance(session, dict):
                continue
            session_id = session.get("id") or entry.get("session_id") or entry.get("sessionId")
            event_id = entry.get("event_id") or entry.get("eventId") or session.get("eventId") or session.get("event_id")
            try:
                session_id = int(session_id)
                event_id = int(event_id)
            except Exception:
                continue
            session = dict(session)
            session.setdefault("id", session_id)
            session.setdefault("eventId", event_id)
            sessions_payloads[session_id] = session
            event_sessions.setdefault(event_id, []).append(session)
        summary["sessions"] = len(sessions_payloads)

    if results_path.exists():
        for entry in open_ndjson(results_path):
            if not isinstance(entry, dict):
                continue
            session_id = entry.get("session_id") or entry.get("sessionId")
            try:
                session_id = int(session_id)
            except Exception:
                continue
            rows = entry.get("results") or entry.get("rows") or []
            if isinstance(rows, list):
                results_payloads[session_id] = rows
        summary["results"] = sum(len(rows) for rows in results_payloads.values())

    if laps_path.exists():
        for entry in open_ndjson(laps_path):
            if not isinstance(entry, dict):
                continue
            session_id = entry.get("session_id") or entry.get("sessionId") or entry.get("session")
            try:
                session_id = int(session_id)
            except Exception:
                continue
            rows = entry.get("rows") or entry.get("rows_list") or entry.get("laps") or []
            if isinstance(rows, list):
                laps_payloads[session_id] = rows
        summary["laps"] = sum(len(rows) for rows in laps_payloads.values())

    if announcements_path.exists():
        for entry in open_ndjson(announcements_path):
            if not isinstance(entry, dict):
                continue
            session_id = entry.get("session_id") or entry.get("sessionId")
            try:
                session_id = int(session_id)
            except Exception:
                continue
            rows = entry.get("announcements") or entry.get("rows") or []
            if isinstance(rows, list):
                announcements_payloads[session_id] = rows
        summary["announcements"] = sum(len(rows) for rows in announcements_payloads.values())

    organization_payload = {"id": org, "name": org_name or f"Organization #{org}"}
    with storage.connect() as conn:
        storage.save_organization(org, organization_payload, conn=conn)
        storage.save_events(org, events_payload, conn=conn)
        for event_id, event_payload in event_payloads.items():
            storage.save_event(event_id, org, event_payload, conn=conn)
            storage.save_event_sessions(event_id, org, event_sessions.get(event_id, []), conn=conn)
        for session_id, session_payload in sessions_payloads.items():
            event_id = int(session_payload.get("eventId") or session_payload.get("event_id"))
            storage.save_session(session_id, event_id, org, session_payload, conn=conn)
            storage.save_results(session_id, event_id, org, results_payloads.get(session_id, []), conn=conn)
            storage.save_laps(session_id, event_id, org, laps_payloads.get(session_id, []), conn=conn)
            storage.save_announcements(session_id, event_id, org, announcements_payloads.get(session_id, []), conn=conn)

        storage.save_refresh_state(
            org,
            {
                "org_id": org,
                "last_refresh_at": None,
                "last_refresh_mode": "imported-dump",
                "events_cached": len(events_payload),
                "sessions_cached": len(sessions_payloads),
                "championships_cached": 0,
                "new_events_detected": 0,
                "refreshed_events": len(events_payload),
                "refreshed_sessions": len(sessions_payloads),
            },
            conn=conn,
        )

    return summary


def ingest_events(in_path: Path, conn: sqlite3.Connection) -> int:
    """Ingest events into analytical_events table."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analytical_events (
            event_id INTEGER PRIMARY KEY,
            name TEXT,
            date TEXT,
            end_date TEXT,
            organization_id INTEGER,
            organization_name TEXT,
            location TEXT,
            country TEXT
        )
        """
    )
    inserted = 0
    for e in open_ndjson(in_path):
        org = e.get("organization", {}) or {}
        raw = e.get("raw") or {}
        event_id = e.get("id") or e.get("eventId") or e.get("event_id") or raw.get("id")
        if event_id is None:
            continue
        try:
            event_id = int(event_id)
        except Exception:
            continue

        name = e.get("name") or e.get("eventName") or e.get("title") or raw.get("name")
        date = e.get("date") or e.get("startDate") or e.get("start_date") or raw.get("startDate")
        end_date = e.get("endDate") or e.get("end_date") or raw.get("endDate")
        org_id = org.get("id") or e.get("organizationId") or e.get("organization_id")
        try:
            org_id = int(org_id) if org_id is not None else None
        except Exception:
            org_id = None
        org_name = org.get("name") or e.get("organizationName")
        location = e.get("location") or e.get("venue") or raw.get("location")
        country = e.get("country") or org.get("country")

        cur.execute(
            "INSERT OR REPLACE INTO analytical_events VALUES (?,?,?,?,?,?,?,?)",
            (event_id, name, date, end_date, org_id, org_name, location, country),
        )
        inserted += 1
    return inserted


def _iter_sessions(record: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    if not record:
        return []
    if isinstance(record.get("sessions"), list):
        return record["sessions"]
    if isinstance(record.get("groups"), list):
        rows: List[Dict[str, Any]] = []
        for group in record["groups"]:
            if isinstance(group, dict) and isinstance(group.get("sessions"), list):
                rows.extend(group["sessions"])
        return rows
    return []


def ingest_sessions(in_path: Path, conn: sqlite3.Connection) -> int:
    """Ingest sessions into analytical_sessions table."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analytical_sessions (
            event_id INTEGER,
            session_id INTEGER PRIMARY KEY,
            name TEXT,
            start_time TEXT,
            end_time TEXT
        )
        """
    )
    inserted = 0
    for record in open_ndjson(in_path):
        rec_event_id = record.get("event_id") or record.get("eventId")
        for session in _iter_sessions(record):
            event_id = session.get("event_id") or session.get("eventId") or session.get("event") or rec_event_id
            session_id = session.get("id") or session.get("sessionId") or session.get("session_id")
            if session_id is None:
                continue
            try:
                session_id = int(session_id)
            except Exception:
                continue
            try:
                event_id = int(event_id) if event_id is not None else None
            except Exception:
                event_id = None

            name = session.get("name") or session.get("sessionName") or session.get("title")
            start_time = session.get("startTime") or session.get("start_time") or session.get("begin")
            end_time = session.get("endTime") or session.get("end_time")

            cur.execute(
                "INSERT OR REPLACE INTO analytical_sessions VALUES (?,?,?,?,?)",
                (event_id, session_id, name, start_time, end_time),
            )
            inserted += 1
    return inserted


def ingest_laps(in_path: Path, conn: sqlite3.Connection) -> int:
    """Ingest laps into laps table."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS laps (
            event_id INTEGER,
            session_id INTEGER,
            competitor_id TEXT,
            lap_number INTEGER,
            lap_time TEXT,
            position INTEGER,
            PRIMARY KEY (session_id, competitor_id, lap_number)
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_laps_event ON laps (event_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_laps_session ON laps (session_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_laps_competitor ON laps (competitor_id)")

    inserted = 0
    for record in open_ndjson(in_path):
        event_id = record.get("event_id") or record.get("eventId")
        session_id = record.get("session_id") or record.get("sessionId")
        try:
            event_id = int(event_id) if event_id is not None else None
        except Exception:
            event_id = None
        try:
            session_id = int(session_id) if session_id is not None else None
        except Exception:
            session_id = None

        rows = record.get("rows") or record.get("lapRows") or record.get("laps") or []
        for r in rows:
            comp_id = r.get("competitorId") or r.get("competitor_id") or r.get("id") or r.get("competitor")
            lap_number = r.get("lapNumber") or r.get("lap_number") or r.get("lap")
            lap_time = r.get("lapTime") or r.get("lap_time") or r.get("time") or r.get("laptime")
            position = r.get("position") or r.get("pos")

            try:
                lap_number = int(lap_number) if lap_number is not None else None
            except Exception:
                lap_number = None
            try:
                position = int(position) if position is not None else None
            except Exception:
                position = None

            if session_id is None or comp_id is None or lap_number is None:
                continue

            cur.execute(
                "INSERT OR REPLACE INTO laps VALUES (?,?,?,?,?,?)",
                (event_id, session_id, comp_id, lap_number, lap_time, position),
            )
            inserted += 1
    return inserted


def _iter_announcements(rec: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    if not rec:
        return []
    if isinstance(rec, list):
        return rec
    if rec.get("announcements"):
        a = rec.get("announcements")
        if isinstance(a, list):
            return a
        if isinstance(a, dict) and isinstance(a.get("rows"), list):
            return a.get("rows")
    if rec.get("rows"):
        return rec.get("rows")
    if rec.get("announcement"):
        return [rec.get("announcement")]
    return []


def ingest_announcements(
    in_path: Path,
    conn: sqlite3.Connection,
    event_names: Dict[int, str],
    session_map: Dict[str, Any],
) -> int:
    """Ingest announcements and parse track records directly into SQLite."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS announcements (
            event_id INTEGER,
            session_id INTEGER,
            ts TEXT,
            text TEXT,
            UNIQUE (session_id, ts, text)
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_announcements_event ON announcements (event_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_announcements_session ON announcements (session_id)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS track_records (
            event_id INTEGER,
            event_name TEXT,
            session_id INTEGER,
            session_name TEXT,
            classification TEXT,
            lap_time TEXT,
            lap_time_seconds REAL,
            driver TEXT,
            marque TEXT,
            timestamp TEXT,
            text TEXT,
            PRIMARY KEY (session_id, text)
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_track_records_event ON track_records (event_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_track_records_class ON track_records (classification)")

    inserted = 0
    for rec in open_ndjson(in_path):
        event_id = rec.get("event_id") or rec.get("eventId")
        session_id = rec.get("session_id") or rec.get("sessionId")
        try:
            event_id = int(event_id) if event_id is not None else None
        except Exception:
            event_id = None
        try:
            session_id = int(session_id) if session_id is not None else None
        except Exception:
            session_id = None

        for a in _iter_announcements(rec):
            text = (a.get("text") or a.get("message") or a.get("body") or "").strip()
            ts = (a.get("time") or a.get("timestamp") or a.get("ts") or "").strip()
            if not text:
                continue

            cur.execute(
                "INSERT OR REPLACE INTO announcements VALUES (?,?,?,?)",
                (event_id, session_id, ts, text),
            )
            inserted += 1

            # Parse track records
            parsed = parse_track_record_text(text)
            if parsed:
                class_name = parsed.get("classification")
                lap_time = parsed.get("lap_time")
                lap_time_seconds = parsed.get("lap_time_seconds")
                driver = parsed.get("driver")
                marque = parsed.get("marque")

                event_name = None
                if event_id is not None:
                    event_name = event_names.get(int(event_id))

                session_name = None
                if session_id is not None:
                    session_name = (session_map.get(str(int(session_id))) or {}).get("name")

                cur.execute(
                    "INSERT OR REPLACE INTO track_records VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        event_id,
                        event_name,
                        session_id,
                        session_name,
                        class_name,
                        lap_time,
                        lap_time_seconds,
                        driver,
                        marque,
                        ts,
                        text,
                    ),
                )

    return inserted


def ingest_results(in_path: Path, conn: sqlite3.Connection) -> int:
    """Ingest results into results table."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            event_id INTEGER,
            session_id INTEGER,
            competitor_id TEXT,
            name TEXT,
            position INTEGER,
            total_time TEXT,
            laps INTEGER,
            best_lap_time TEXT,
            PRIMARY KEY (session_id, competitor_id)
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_results_event ON results (event_id)")

    inserted = 0
    for record in open_ndjson(in_path):
        event_id = record.get("event_id") or record.get("eventId")
        session_id = record.get("session_id") or record.get("sessionId")
        try:
            event_id = int(event_id) if event_id is not None else None
        except Exception:
            event_id = None
        try:
            session_id = int(session_id) if session_id is not None else None
        except Exception:
            session_id = None

        rows = record.get("results") or record.get("rows") or []
        for r in rows:
            competitor = r.get("competitor") or {}
            comp_id = r.get("competitorId") or competitor.get("id") or r.get("id") or r.get("competitor_id")
            name = r.get("name") or competitor.get("name")
            pos = r.get("position") or r.get("pos")
            total_time = r.get("totalTime") or r.get("total_time")
            laps = r.get("laps") or r.get("lapCount")
            best_lap_time = r.get("bestLapTime") or r.get("best_lap_time") or r.get("bestLap")

            try:
                pos = int(pos) if pos is not None else None
            except Exception:
                pos = None
            try:
                laps = int(laps) if laps is not None else None
            except Exception:
                laps = None

            if session_id is None or comp_id is None:
                continue

            cur.execute(
                "INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?,?,?)",
                (event_id, session_id, comp_id, name, pos, total_time, laps, best_lap_time),
            )
            inserted += 1
    return inserted


def load_event_names(events_path: Path) -> Dict[int, str]:
    """Helper to read events from NDJSON and return a mapping of ID to Name."""
    event_names: Dict[int, str] = {}
    if events_path.exists():
        for event in open_ndjson(events_path):
            event_id = event.get("event_id") or event.get("eventId") or (event.get("raw") or {}).get("id")
            if event_id is None:
                continue
            try:
                event_id_int = int(event_id)
            except Exception:
                continue
            event_names[event_id_int] = event.get("event_name") or (event.get("raw") or {}).get("name") or ""
    return event_names


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Import an offline NDJSON(.gz) dump into the primary SQLite cache")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Root directory containing exported NDJSON dump files")
    parser.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    args = parser.parse_args(argv)

    summary = import_dump_to_storage(args.org, args.dump_dir, args.db_path)

    # Ingest analytical tables
    dump = args.dump_dir / str(args.org)
    if dump.exists():
        event_names = load_event_names(_prefer_gz(dump / "events.ndjson"))
        session_map = load_session_map(args.dump_dir, args.org)

        conn = sqlite3.connect(args.db_path)
        try:
            ingest_events(_prefer_gz(dump / "events.ndjson"), conn)
            ingest_sessions(_prefer_gz(dump / "sessions.ndjson"), conn)
            ingest_laps(_prefer_gz(dump / "laps.ndjson"), conn)
            ingest_announcements(_prefer_gz(dump / "announcements.ndjson"), conn, event_names, session_map)
            ingest_results(_prefer_gz(dump / "results.ndjson"), conn)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise exc
        finally:
            conn.close()

    print(f"Imported dump for org {args.org} into primary cache: {args.db_path}")
    print(
        f"events={summary['events']} sessions={summary['sessions']} "
        f"results={summary['results']} laps={summary['laps']} announcements={summary['announcements']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
