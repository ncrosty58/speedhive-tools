"""Import offline NDJSON(.gz) dumps into a local SQLite database."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List

from speedhive.processing.ndjson import open_ndjson


def ingest_events(in_path: Path, conn: sqlite3.Connection) -> int:
    """Ingest events into events table."""
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS events")
    cur.execute(
        """
        CREATE TABLE events (
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
            "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?)",
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
    """Ingest sessions into sessions table."""
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS sessions")
    cur.execute(
        """
        CREATE TABLE sessions (
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
                "INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?)",
                (event_id, session_id, name, start_time, end_time),
            )
            inserted += 1
    return inserted


def ingest_laps(in_path: Path, conn: sqlite3.Connection) -> int:
    """Ingest laps into laps table."""
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS laps")
    cur.execute(
        """
        CREATE TABLE laps (
            event_id INTEGER,
            session_id INTEGER,
            competitor_id TEXT,
            lap_number INTEGER,
            lap_time TEXT,
            position INTEGER
        )
        """
    )
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

            cur.execute(
                "INSERT INTO laps VALUES (?,?,?,?,?,?)",
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


def ingest_announcements(in_path: Path, conn: sqlite3.Connection) -> int:
    """Ingest announcements into announcements table."""
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS announcements")
    cur.execute(
        """
        CREATE TABLE announcements (
            event_id INTEGER,
            session_id INTEGER,
            ts TEXT,
            text TEXT
        )
        """
    )
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
            text = a.get("text") or a.get("message") or a.get("body")
            ts = a.get("time") or a.get("timestamp") or a.get("ts")
            cur.execute(
                "INSERT INTO announcements VALUES (?,?,?,?)",
                (event_id, session_id, ts, text),
            )
            inserted += 1
    return inserted


def ingest_results(in_path: Path, conn: sqlite3.Connection) -> int:
    """Ingest results into results table."""
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS results")
    cur.execute(
        """
        CREATE TABLE results (
            event_id INTEGER,
            session_id INTEGER,
            competitor_id TEXT,
            name TEXT,
            position INTEGER,
            total_time TEXT,
            laps INTEGER,
            best_lap_time TEXT
        )
        """
    )
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

            cur.execute(
                "INSERT INTO results VALUES (?,?,?,?,?,?,?,?)",
                (event_id, session_id, comp_id, name, pos, total_time, laps, best_lap_time),
            )
            inserted += 1
    return inserted


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Import offline NDJSON(.gz) organization dumps into SQLite")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Root dump directory")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory for SQLite DB (defaults to dump-dir/<org>/)")
    args = parser.parse_args(argv)

    dump = args.dump_dir / str(args.org)
    if not dump.exists():
        print(f"Dump directory for organization {args.org} does not exist at: {dump}")
        return 1

    out_dir = args.out_dir or dump
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / f"laps_{args.org}.db"

    conn = sqlite3.connect(db_path)
    try:
        # 1. Events
        events_path = dump / "events.ndjson.gz"
        if not events_path.exists():
            events_path = dump / "events.ndjson"
        if events_path.exists():
            cnt = ingest_events(events_path, conn)
            print(f"Ingested {cnt} events")
        else:
            print("No events file found, skipping.")

        # 2. Sessions
        sessions_path = dump / "sessions.ndjson.gz"
        if not sessions_path.exists():
            sessions_path = dump / "sessions.ndjson"
        if sessions_path.exists():
            cnt = ingest_sessions(sessions_path, conn)
            print(f"Ingested {cnt} sessions")
        else:
            print("No sessions file found, skipping.")

        # 3. Laps
        laps_path = dump / "laps.ndjson.gz"
        if not laps_path.exists():
            laps_path = dump / "laps.ndjson"
        if laps_path.exists():
            cnt = ingest_laps(laps_path, conn)
            print(f"Ingested {cnt} laps")
        else:
            print("No laps file found, skipping.")

        # 4. Announcements
        announcements_path = dump / "announcements.ndjson.gz"
        if not announcements_path.exists():
            announcements_path = dump / "announcements.ndjson"
        if announcements_path.exists():
            cnt = ingest_announcements(announcements_path, conn)
            print(f"Ingested {cnt} announcements")
        else:
            print("No announcements file found, skipping.")

        # 5. Results
        results_path = dump / "results.ndjson.gz"
        if not results_path.exists():
            results_path = dump / "results.ndjson"
        if results_path.exists():
            cnt = ingest_results(results_path, conn)
            print(f"Ingested {cnt} results")
        else:
            print("No results file found, skipping.")

        conn.commit()
        print(f"Database successfully updated at: {db_path}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
