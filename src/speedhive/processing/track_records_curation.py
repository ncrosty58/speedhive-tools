"""Generic, per-organization track-records curation: sync/diff + storage.

Pulls Speedhive's announcer-flagged "New Track/Class Record" data for a given
org, normalizes classification tokens against that org's own alias map (no
hardcoded org-specific data lives here), and diffs against a per-org curated
file -- new/changed rows only ever land in a per-org candidates_pending.ndjson
for a human to review, never written to curated.ndjson directly.

Row-shaped data (curated records, pending candidates, rejected entries) is
stored as NDJSON (see speedhive.ndjson for the format convention);
config-shaped files (class alias map, notification settings, task state) are
plain JSON documents.

Works for any org_id; nothing here is specific to any one club/organization.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from speedhive.exporters.export_track_records_history import save_candidates_history_ndjson
from speedhive.processing.refresh_org_cache import refresh_org_cache
from speedhive.processing.track_records import extract_records_from_storage
from speedhive.processing.track_records_store import (
    load_candidates,
    load_curated,
    load_json,
    load_rejected,
    paths_for_org,
    save_candidates,
    save_curated,
    save_json,
    save_rejected,
)
from speedhive.storage import SpeedhiveStorage

GOTIFY_URL = os.environ.get("GOTIFY_URL")
GOTIFY_APP_TOKEN = os.environ.get("GOTIFY_APP_TOKEN")
# Speedhive syncs are slow (lots of data per event) -- only re-sync if the
# cache is older than this, unless the caller explicitly forces it.
DEFAULT_STALE_AFTER_HOURS = float(os.environ.get("TRACK_RECORDS_STALE_HOURS", "20"))

def lap_time_to_seconds(lap_time):
    """Parse 'm:ss.mmm' or 'ss.mmm' into float seconds; None if unparseable.

    Stricter than process_lap_analysis.parse_time_value on purpose: this one
    is used to validate human-supplied lap times, so it must reject junk
    rather than salvage digits out of it.
    """
    if not lap_time:
        return None
    parts = str(lap_time).split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except ValueError:
        return None


def normalize_classification(raw_token, alias_map):
    """Returns (status, resolved_abbreviation). status: 'ok' | 'ambiguous'.

    No canonical whitelist is required -- any token is accepted as-is (upper/
    trimmed) unless it's in this org's `always_review` list (for tokens that
    are genuinely ambiguous, e.g. a combined class group that splits into
    multiple record-keeping classes). The human review step is the real
    safety net for typos/unexpected tokens, not a whitelist.
    """
    if not raw_token:
        return "ambiguous", None
    token = raw_token.strip().upper()

    if token in {t.strip().upper() for t in alias_map.get("always_review", [])}:
        return "ambiguous", None

    aliases = {k.strip().upper(): v for k, v in alias_map.get("aliases", {}).items()}
    if token in aliases:
        token = aliases[token].strip().upper()

    return "ok", token


def notify_gotify(title, message):
    if not GOTIFY_URL or not GOTIFY_APP_TOKEN:
        return
    try:
        data = urllib.parse.urlencode({"title": title, "message": message, "priority": 5}).encode()
        url = f"{GOTIFY_URL.rstrip('/')}/message?token={GOTIFY_APP_TOKEN}"
        urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=10)
    except Exception as exc:
        print(f"Gotify notification failed: {exc}", file=sys.stderr)


def build_curated_fastest_index(curated):
    """Map classAbbreviation -> fastest curated record (dict, plus '_seconds')."""
    fastest = {}
    for r in curated.get("records", []):
        cls = r["classAbbreviation"]
        secs = lap_time_to_seconds(r.get("lapTime"))
        if secs is None:
            continue
        if cls not in fastest or secs < fastest[cls]["_seconds"]:
            entry = dict(r)
            entry["_seconds"] = secs
            fastest[cls] = entry
    return fastest


def rejected_key(classAbbreviation, lapTime, driverName, date):
    return (classAbbreviation, lapTime, driverName, date)


_online_status_cache = {}


def get_cache_status(org_id, db_path, track_records_root, client=None):
    """Freshness info for the Speedhive cache -- queries Speedhive dynamically if client is provided."""
    p = paths_for_org(track_records_root, org_id)
    db_path = Path(db_path)

    candidates_payload = load_candidates(p)
    pending_candidates = len(candidates_payload.get("candidates", []))

    stale_after_hours = DEFAULT_STALE_AFTER_HOURS

    last_refresh_at = None
    age_hours = None
    needs_sync_local = True

    if db_path.exists():
        try:
            storage = SpeedhiveStorage(db_path)
            state = storage.get_org_status(org_id) or {}
            last_refresh_at = state.get("last_refresh_at")
            if last_refresh_at:
                last_dt = datetime.fromisoformat(str(last_refresh_at).replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600.0
                needs_sync_local = age_hours >= stale_after_hours
        except Exception:
            pass

    # Check if we have a fresh cached result (within 5 minutes)
    now = time.time()
    if org_id in _online_status_cache:
        cached_time, cached_needs_sync, cached_check_source = _online_status_cache[org_id]
        if now - cached_time < 300:  # 5 minutes
            return {
                "org_id": org_id,
                "last_synced_at": last_refresh_at,
                "age_hours": age_hours,
                "needs_sync": cached_needs_sync,
                "stale_after_hours": stale_after_hours,
                "pending_candidates": pending_candidates,
                "check_source": f"{cached_check_source} (cached)"
            }

    needs_sync = needs_sync_local
    check_source = "local_age"

    if client and db_path.exists():
        try:
            # Query Speedhive's latest 5 events for this organization
            online_events = client.get_events(org_id, limit=5) or []
            if online_events:
                storage = SpeedhiveStorage(db_path)
                cached_events = storage.get_events(org_id) or []
                cached_ids = {e.get("id") for e in cached_events if e.get("id")}

                # 1. Check for new event IDs not present in cache
                has_new_events = False
                for event in online_events:
                    eid = event.get("id")
                    if eid and eid not in cached_ids:
                        has_new_events = True
                        break

                if has_new_events:
                    needs_sync = True
                    check_source = "new_events_found"
                else:
                    # 2. Check if any online event has been updated since our last sync
                    if last_refresh_at:
                        last_dt = datetime.fromisoformat(str(last_refresh_at).replace("Z", "+00:00"))
                        has_updates = False
                        for event in online_events:
                            updated_at = event.get("updatedAt")
                            if updated_at:
                                try:
                                    updated_dt = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
                                    if updated_dt > last_dt:
                                        has_updates = True
                                        break
                                except Exception:
                                    pass

                        if has_updates:
                            needs_sync = True
                            check_source = "event_updates_found"
                        else:
                            # Local cache matches Speedhive latest events perfectly!
                            needs_sync = False
                            check_source = "online_match"
                    else:
                        needs_sync = True
                        check_source = "never_synced"
            else:
                needs_sync = False
                check_source = "no_online_events"

            # Cache the status check
            _online_status_cache[org_id] = (now, needs_sync, check_source)

        except Exception as exc:
            print(f"[StatusCheck] Failed to fetch online status for Org {org_id}: {str(exc)}", file=sys.stderr)
            check_source = f"local_age_fallback ({str(exc)})"

    return {
        "org_id": org_id,
        "last_synced_at": last_refresh_at,
        "age_hours": age_hours,
        "needs_sync": needs_sync,
        "stale_after_hours": stale_after_hours,
        "pending_candidates": pending_candidates,
        "check_source": check_source
    }


def run_sync_and_diff(org_id, db_path, track_records_root, progress_cb=None):
    """Extract + normalize + diff for one org, against the already-synced cache
    at db_path. Does NOT perform the Speedhive sync itself -- callers are
    responsible for refreshing db_path first if needed (e.g. via the generic
    refresh_org_cache machinery). Returns a summary dict.
    """
    def report(phase):
        if progress_cb:
            progress_cb(phase)

    p = paths_for_org(track_records_root, org_id)
    db_path = Path(db_path)
    if not db_path.exists():
        raise RuntimeError(f"No cache at {db_path}; sync the org first.")

    report("Extracting announcer-flagged records")
    raw_records = extract_records_from_storage(org_id, db_path)

    report("Normalizing and diffing against curated records")
    alias_map = load_json(p["alias_map"], {"aliases": {}, "always_review": []})
    curated = load_curated(p)
    rejected_rows = load_rejected(p).get("rejected", [])
    rejected_keys = {
        rejected_key(r.get("classAbbreviation"), r.get("lapTime"), r.get("driverName"), r.get("date"))
        for r in rejected_rows
    }

    curated_fastest = build_curated_fastest_index(curated)

    best_by_class = {}
    flagged = []
    seen_flagged_keys = set()

    for row in raw_records:
        status, resolved = normalize_classification(row.get("classification"), alias_map)
        secs = row.get("lap_time_seconds")
        if secs is None:
            secs = lap_time_to_seconds(row.get("lap_time"))
        ts = row.get("timestamp")
        date_str = str(ts)[:10] if ts else None

        if status != "ok":
            key = rejected_key(row.get("classification"), row.get("lap_time"), row.get("driver"), date_str)
            if key in rejected_keys or key in seen_flagged_keys:
                continue
            seen_flagged_keys.add(key)
            flagged.append({
                "action": "unmapped_classification",
                "reason": status,
                "current": None,
                "proposed": {
                    "classAbbreviation": row.get("classification"),
                    "lapTime": row.get("lap_time"),
                    "driverName": row.get("driver"),
                    "marque": row.get("marque"),
                    "date": date_str,
                },
                "raw": {
                    "event_name": row.get("event_name"),
                    "session_name": row.get("session_name"),
                    "text": row.get("text"),
                },
            })
            continue

        if secs is None:
            continue
        if resolved not in best_by_class or secs < best_by_class[resolved]["_seconds"]:
            entry = dict(row)
            entry["_seconds"] = secs
            entry["_resolved"] = resolved
            entry["_date"] = date_str
            best_by_class[resolved] = entry

    candidates = []
    for cls, entry in best_by_class.items():
        proposed = {
            "classAbbreviation": cls,
            "lapTime": entry.get("lap_time"),
            "driverName": entry.get("driver"),
            "marque": entry.get("marque"),
            "date": entry.get("_date"),
        }
        key = rejected_key(cls, proposed["lapTime"], proposed["driverName"], proposed["date"])
        if key in rejected_keys:
            continue

        current = curated_fastest.get(cls)
        if current is not None and entry["_seconds"] >= current["_seconds"]:
            continue  # Speedhive doesn't know a time faster than what's already curated

        current_public = None
        if current is not None:
            current_public = {k: current[k] for k in ("classAbbreviation", "lapTime", "driverName", "marque", "date")}

        candidates.append({
            "action": "new_record",
            "classAbbreviation": cls,
            "current": current_public,
            "proposed": proposed,
            "raw": {
                "event_name": entry.get("event_name"),
                "session_name": entry.get("session_name"),
                "text": entry.get("text"),
            },
        })

    candidates.extend(flagged)

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "org_id": org_id,
        "candidates": candidates,
    }
    save_candidates(p, payload)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    save_candidates_history_ndjson(p["history"] / f"candidates_{stamp}.ndjson", payload)

    new_count = sum(1 for c in candidates if c["action"] == "new_record")
    unmapped_count = sum(1 for c in candidates if c["action"] == "unmapped_classification")

    if candidates:
        notify_gotify(
            f"Track records: new candidates for org {org_id}",
            f"{len(candidates)} candidate(s) waiting for review at /org/{org_id}/track-records/review "
            f"({new_count} new record(s), {unmapped_count} unmapped classification(s)).",
        )

    report("Done")
    return {
        "raw_records_scanned": len(raw_records),
        "candidates_found": len(candidates),
        "new_record_candidates": new_count,
        "unmapped_candidates": unmapped_count,
        "generated_at": payload["generated_at"],
    }


def refresh_and_scan(
    org_id,
    client,
    db_path,
    track_records_root,
    *,
    mode: str = "incremental",
    force: bool = False,
    max_events=None,
    recent_backfill_events: int = 20,
    cleanup_on_full: bool = True,
    progress_cb=None,
):
    """Refresh the org cache if needed, then run the track-record scan.

    This is the single orchestration entrypoint used by the UI and CLI when
    they want the full update flow instead of only diffing an already-synced
    cache.
    """
    def report(phase):
        if progress_cb:
            progress_cb(phase)

    status = get_cache_status(org_id, db_path, track_records_root, client=client)
    refresh_result = None
    if force or status["needs_sync"]:
        report("Refreshing Speedhive cache")
        refresh_result = refresh_org_cache(
            client=client,
            org_id=org_id,
            mode=mode,
            max_events=max_events,
            recent_backfill_events=recent_backfill_events if mode != "full" else 0,
            cleanup_on_full=cleanup_on_full,
            db_path=db_path,
        )
    else:
        age_str = f"{status['age_hours']:.1f}h" if status.get("age_hours") is not None else "unknown age"
        report(f"Speedhive cache is fresh ({age_str} old), skipping refresh")

    report("Scanning cached Speedhive data for track records")
    scan_result = run_sync_and_diff(org_id, db_path, track_records_root, progress_cb=progress_cb)
    return {
        "status": status,
        "refresh": refresh_result,
        "scan": scan_result,
        "refresh_ran": refresh_result is not None,
    }
