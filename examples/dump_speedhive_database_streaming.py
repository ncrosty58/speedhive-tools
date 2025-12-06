
#!/usr/bin/env python3
"""
Low-RAM streaming dump of Speedhive Event Results to disk (NDJSON per line).

Design goals:
- No big lists in memory: write each row as soon as it arrives.
- On-disk dedupe and progress tracking via SQLite (tiny footprint).
- Append-only outputs so you can resume or run in batches.

Outputs (under ./dump):
  dump/events_global.ndjson                  # global events stream
  dump/organizations_discovered.ndjson       # org ids as discovered (may contain duplicates)
  dump/organizations_detailed.ndjson         # one detailed org profile per line
  dump/org_{ORG_ID}/events.ndjson            # org-scoped events (streamed)
  dump/org_{ORG_ID}/sessions.ndjson          # sessions for those events (streamed)
  dump/org_{ORG_ID}/announcements.ndjson     # announcements per session (streamed)
  dump/org_{ORG_ID}/records.json             # normalized records via client exporter
  dump/org_{ORG_ID}/lapdata.ndjson           # lap rows per session + position (NEW)

You can safely re-run; processed orgs are marked in SQLite and skipped.
"""

import os
import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, Any, Iterable, Optional

from speedhive_tools.client import SpeedHiveClient, SpeedHiveAPIError  # your client

# ---------- CONFIG ----------
BASE_URL = "https://eventresults-api.speedhive.com/api/v0.2.3/eventresults"
SPORT = "All"
SPORT_CATEGORY = "Motorized"
COUNT_PER_PAGE = 200              # larger pages → fewer requests
RATE_DELAY = 0.25                 # small pacing between batches
TIMEOUT = 30
RETRIES = 3

OUT_DIR = Path("dump")
OUT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = OUT_DIR / "index.sqlite"  # org ids + progress, on disk
API_KEY = os.getenv("SPEEDHIVE_API_KEY", None)

FLUSH_EVERY = 500                  # flush buffers every N writes

# ---------- Streaming writer ----------
class NDJSONStream:
    def __init__(self, path: Path, flush_every: int = FLUSH_EVERY):
        self.path = path
        self.flush_every = max(1, int(flush_every))
        self._fh = None
        self._count_since_flush = 0

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")
        return self

    def write(self, obj: Dict[str, Any]):
        self._fh.write(json.dumps(obj, ensure_ascii=False))
        self._fh.write("\n")
        self._count_since_flush += 1
        if self._count_since_flush >= self.flush_every:
            self._fh.flush()
            os.fsync(self._fh.fileno())
            self._count_since_flush = 0

    def __exit__(self, exc_type, exc, tb):
        if self._fh:
            self._fh.flush()
            os.fsync(self._fh.fileno())
            self._fh.close()

# ---------- SQLite (on-disk dedupe + progress) ----------
def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS orgs (id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS progress (org_id INTEGER PRIMARY KEY, processed INTEGER DEFAULT 0)")
    return conn

def db_upsert_org(conn: sqlite3.Connection, org_id: int):
    conn.execute("INSERT OR IGNORE INTO orgs(id) VALUES(?)", (org_id,))
    conn.commit()

def db_mark_processed(conn: sqlite3.Connection, org_id: int):
    conn.execute("INSERT INTO progress(org_id, processed) VALUES(?, 1) ON CONFLICT(org_id) DO UPDATE SET processed=1", (org_id,))
    conn.commit()

def db_iter_unprocessed_orgs(conn: sqlite3.Connection):
    cur = conn.execute("""
        SELECT o.id
        FROM orgs o
        LEFT JOIN progress p ON p.org_id = o.id
        WHERE IFNULL(p.processed, 0) = 0
        ORDER BY o.id ASC
    """)
    for (oid,) in cur:
        yield int(oid)

# ---------- Utilities ----------
def pick_first(d: Dict[str, Any], names: Iterable[str], default=None):
    for n in names:
        v = d.get(n)
        if v is not None:
            return v
    return default

def to_int_or_none(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except Exception:
        return None

def extract_org_id(ev: Dict[str, Any]) -> Optional[int]:
    cand = pick_first(ev, ("organizationId", "orgId", "organisationId", "organization_id"), None)
    if cand is None:
        org = ev.get("organization") or ev.get("organisation")
        if isinstance(org, dict):
            cand = pick_first(org, ("id", "organizationId", "orgId"), None)
    return to_int_or_none(cand)

def extract_event_id(ev: Dict[str, Any]) -> Optional[int]:
    return to_int_or_none(pick_first(ev, ("id", "eventId", "event_id"), None))

# ---------- Crawl (streaming) ----------
def crawl_global_events_streaming(client: SpeedHiveClient, conn: sqlite3.Connection):
    print(f"[global] streaming events with sport={SPORT} category={SPORT_CATEGORY} …")
    events_path = OUT_DIR / "events_global.ndjson"
    orgs_discovered_path = OUT_DIR / "organizations_discovered.ndjson"
    # streaming writers
    with NDJSONStream(events_path) as ev_writer, NDJSONStream(orgs_discovered_path) as org_writer:
        total = 0
        for ev in client._paginate_offset(
            path="/events",
            count=COUNT_PER_PAGE,
            start_offset=0,
            params={"sport": SPORT, "sportCategory": SPORT_CATEGORY},
            max_items=None,
        ):
            if not isinstance(ev, dict):
                continue
            ev_writer.write(ev)
            total += 1
            oid = extract_org_id(ev)
            if oid is not None:
                # write discovered org id (could be duplicates; we dedupe in SQLite)
                org_writer.write({"organizationId": oid})
                db_upsert_org(conn, oid)
            if RATE_DELAY:
                time.sleep(RATE_DELAY / 10.0)  # very small pacing per item
    print(f"[global] wrote {total:,} event rows")

def process_one_org(client: SpeedHiveClient, conn: sqlite3.Connection, org_id: int):
    print(f"[org {org_id}] start")
    org_dir = OUT_DIR / f"org_{org_id}"
    org_dir.mkdir(parents=True, exist_ok=True)

    # 1) org profile → append to NDJSON
    org_detail_path = OUT_DIR / "organizations_detailed.ndjson"
    try:
        org_obj = client.get_organization(org_id)
        # serialize defensively
        payload = getattr(org_obj, "__dict__", None)
        if not isinstance(payload, dict):
            payload = {"id": org_id}
        with NDJSONStream(org_detail_path) as org_writer:
            org_writer.write(payload)
    except SpeedHiveAPIError as e:
        print(f"[org {org_id}] ERROR get_organization: {e}")

    # 2) org events → stream
    events_path = org_dir / "events.ndjson"
    with NDJSONStream(events_path) as ev_writer:
        count_events = 0
        for ev in client._paginate_offset(
            path=f"/{client._orgs_prefix()}/{org_id}/events",
            count=COUNT_PER_PAGE,
            start_offset=0,
            params=None,
            max_items=None,
        ):
            if isinstance(ev, dict):
                ev_writer.write(ev)
                count_events += 1
            if RATE_DELAY:
                time.sleep(RATE_DELAY / 10.0)
    print(f"[org {org_id}] events={count_events:,}")

    # 3) sessions & 4) announcements → stream (no lists kept)
    sessions_path = org_dir / "sessions.ndjson"
    announcements_path = org_dir / "announcements.ndjson"
    with NDJSONStream(sessions_path) as sess_writer, NDJSONStream(announcements_path) as ann_writer:
        # iterate events from file (streamed) to stay consistent and low-RAM
        count_sessions = 0
        count_ann = 0
        # iterate events from file
        with events_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                ev_id = extract_event_id(ev)
                if not ev_id:
                    continue

                # sessions for event
                try:
                    sessions = client.get_sessions_for_event(ev_id)
                except SpeedHiveAPIError as e:
                    print(f"[event {ev_id}] ERROR get_sessions_for_event: {e}")
                    sessions = []

                # stream sessions and fetch announcements per session
                for s in sessions:
                    s["eventId"] = ev_id
                    sess_writer.write(s)
                    count_sessions += 1
                    sid = s.get("id")
                    if not sid:
                        continue

                    # announcements for session
                    try:
                        rows = client.get_session_announcements(int(sid))
                    except SpeedHiveAPIError as e:
                        print(f"[session {sid}] ERROR get_session_announcements: {e}")
                        rows = []
                    for a in rows:
                        a["eventId"] = ev_id
                        a["sessionId"] = int(sid)
                        ann_writer.write(a)
                        count_ann += 1

                    # lapdata for session (positions 1..N) (NEW)
                    try:
                        lap_written = stream_session_lapdata(client, org_dir, ev_id, int(sid))
                        if lap_written:
                            print(f"[session {sid}] lapdata rows={lap_written}")
                    except SpeedHiveAPIError as e:
                        print(f"[session {sid}] ERROR stream_session_lapdata: {e}")

                    if RATE_DELAY:
                        time.sleep(RATE_DELAY / 5.0)
    print(f"[org {org_id}] sessions={count_sessions:,} announcements={count_ann:,}")

    # 5) records via helper (writes JSON per org)
    try:
        rec_count = client.export_records_to_json_camel(org_id, str(org_dir / "records.json"))
        print(f"[org {org_id}] records.json entries={rec_count}")
    except SpeedHiveAPIError as e:
        print(f"[org {org_id}] ERROR export_records_to_json_camel: {e}")

    # mark processed
    db_mark_processed(conn, org_id)
    print(f"[org {org_id}] done")

# --- Lap data streaming (NEW) ---
LAPDATA_TOP_N = int(os.getenv("LAPDATA_TOP_N", "3"))  # positions 1..N per session

def stream_session_lapdata(client: SpeedHiveClient, org_dir: Path, ev_id: int, session_id: int) -> int:
    """
    Fetch lap data for positions 1..LAPDATA_TOP_N for a session and append to NDJSON.
    Returns number of lap rows written.
    """
    out_path = org_dir / "lapdata.ndjson"
    written = 0
    with NDJSONStream(out_path) as lap_writer:
        for pos in range(1, max(1, LAPDATA_TOP_N) + 1):
            try:
                rows = client.get_session_lap_data(session_id, pos)
            except SpeedHiveAPIError as e:
                print(f"[session {session_id}] ERROR get_session_lap_data pos={pos}: {e}")
                rows = []
            for r in rows:
                if isinstance(r, dict):
                    r = dict(r)
                    r.setdefault("eventId", ev_id)
                    r.setdefault("sessionId", session_id)
                    r.setdefault("position", pos)
                lap_writer.write(r)
                written += 1
            if RATE_DELAY:
                time.sleep(RATE_DELAY / 10.0)
    return written

def main():
    client = SpeedHiveClient(
        api_key=API_KEY,
        rate_delay=RATE_DELAY,
        base_url=BASE_URL,
        timeout=TIMEOUT,
        retries=RETRIES,
        pool_connections=20,
        pool_maxsize=40,
    )
    conn = db_connect()

    # A) Stream global events and discover org IDs (on-disk dedupe)
    crawl_global_events_streaming(client, conn)

    # B) Process each unprocessed org, one by one
    for org_id in db_iter_unprocessed_orgs(conn):
        process_one_org(client, conn, org_id)
        # small gap between orgs to be nice to the API
        if RATE_DELAY:
            time.sleep(RATE_DELAY)

    print("[done] outputs in ./dump")

if __name__ == "__main__":
    main()
