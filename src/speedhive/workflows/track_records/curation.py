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

from speedhive.ndjson import save_ndjson
from speedhive.workflows.refresh_org_cache import refresh_org_cache
from speedhive.stores.track_records import (
    load_candidates,
    load_curated,
    load_json,
    load_parse_cache,
    load_rejected,
    paths_for_org,
    save_candidates,
    save_curated,
    save_json,
    save_parse_cache,
    save_rejected,
)

GOTIFY_URL = os.environ.get("GOTIFY_URL")
GOTIFY_APP_TOKEN = os.environ.get("GOTIFY_APP_TOKEN")
# Speedhive syncs are slow (lots of data per event) -- only re-sync if the
# cache is older than this, unless the caller explicitly forces it.
DEFAULT_STALE_AFTER_HOURS = float(os.environ.get("TRACK_RECORDS_STALE_HOURS", "20"))

def lap_time_to_seconds(lap_time):
    """Parse 'm:ss.mmm' or 'ss.mmm' into float seconds; None if unparseable.

    Stricter than analysis.lap_analysis.parse_time_value on purpose: this one
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


def normalize_identity_part(val):
    if val is None:
        return ""
    return str(val).strip().upper()


def make_ldc(cls, lap, driver):
    return (
        normalize_identity_part(cls),
        normalize_identity_part(lap),
        normalize_identity_part(driver)
    )


def rejected_key(classAbbreviation, lapTime, driverName, date):
    return (
        normalize_identity_part(classAbbreviation),
        normalize_identity_part(lapTime),
        normalize_identity_part(driverName),
        normalize_identity_part(date)
    )


def _utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _find_by_identity(records, identity):
    norm_identity = tuple(normalize_identity_part(x) for x in identity)
    return next(
        (r for r in records
         if rejected_key(r.get("classAbbreviation"), r.get("lapTime"), r.get("driverName"), r.get("date")) == norm_identity),
        None,
    )


def add_curated_record(p, fields):
    """Manually add a curated record (not derived from a scan candidate).

    `fields` is a dict with classAbbreviation/lapTime/driverName/marque/date.
    Returns the saved record, or None if a required field is missing.
    """
    record = {
        "classAbbreviation": (fields.get("classAbbreviation") or "").strip(),
        "lapTime": (fields.get("lapTime") or "").strip(),
        "driverName": (fields.get("driverName") or "").strip(),
        "marque": (fields.get("marque") or "").strip() or None,
        "date": (fields.get("date") or "").strip(),
        "addedAt": _utc_now_iso(),
        "source": "manual",
    }
    if not record["classAbbreviation"] or not record["lapTime"] or not record["date"]:
        return None

    curated = load_curated(p)
    curated.setdefault("records", []).append(record)
    curated["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    save_curated(p, curated)
    return record


def edit_curated_record(p, orig_identity, fields):
    """Update an existing curated record's fields, matched by its original
    identity (since editing changes the very fields used to identify it).

    Speedhive-sourced records get flagged `modified` so it's visible a human
    has since corrected announcer-derived data; manual records don't need the
    flag, they're already fully human-owned.

    Returns the updated record, or None if not found / a required field is missing.
    """
    updated = {
        "classAbbreviation": (fields.get("classAbbreviation") or "").strip(),
        "lapTime": (fields.get("lapTime") or "").strip(),
        "driverName": (fields.get("driverName") or "").strip(),
        "marque": (fields.get("marque") or "").strip() or None,
        "date": (fields.get("date") or "").strip(),
    }
    if not updated["classAbbreviation"] or not updated["lapTime"] or not updated["date"]:
        return None

    curated = load_curated(p)
    target = _find_by_identity(curated.get("records", []), orig_identity)
    if target is None:
        return None

    target.update(updated)
    if target.get("source") != "manual":
        target["modified"] = True
        target["modified_at"] = _utc_now_iso()

    curated["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    save_curated(p, curated)
    return target


def dedupe_curated_speedhive_additions(p):
    """Remove curated rows that duplicate an already-curated (class, lap
    time, driver) -- same real record, just computed with a different date
    than the pre-existing entry (see run_sync_and_diff's identity match,
    which used to include date and so treated these as new).

    Only removes a `source == "speedhive"` row when a pre-existing
    (non-"speedhive") row already covers the same (class, lapTime,
    driverName); the pre-existing row always wins and is kept as-is. Groups
    where every entry is pre-existing are left untouched -- that's a
    separate, longer-standing data question, not this specific bug.

    Returns {"removed": int, "removed_records": [dict, ...]}.
    """
    curated = load_curated(p)
    records = curated.get("records", [])

    groups = {}
    for r in records:
        key = (r.get("classAbbreviation"), r.get("lapTime"), r.get("driverName"))
        groups.setdefault(key, []).append(r)

    to_remove = []
    for rows in groups.values():
        if len(rows) < 2:
            continue
        pre_existing = [r for r in rows if r.get("source") != "speedhive"]
        added_today = [r for r in rows if r.get("source") == "speedhive"]
        if pre_existing and added_today:
            to_remove.extend(added_today)

    if to_remove:
        remove_ids = {id(r) for r in to_remove}
        curated["records"] = [r for r in records if id(r) not in remove_ids]
        curated["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        save_curated(p, curated)

    return {"removed": len(to_remove), "removed_records": to_remove}


def approve_all_candidates(p, only_action="new_record"):
    """Approve every pending candidate matching `only_action` straight into
    curated, using each candidate's own proposed values as-is.

    All pending candidates have action "new_record" -- anything the parser
    flagged as unsure (ambiguous classification, low-confidence LLM
    extraction) is routed straight to rejected by run_sync_and_diff and never
    reaches this queue.

    Returns {"approved": int, "skipped": int} (skipped = candidates left
    behind that didn't match only_action).
    """
    payload = load_candidates(p)
    candidates = payload.get("candidates", [])
    to_approve = [c for c in candidates if c.get("action") == only_action]
    remaining = [c for c in candidates if c.get("action") != only_action]

    if to_approve:
        curated = load_curated(p)
        for c in to_approve:
            proposed = c.get("proposed", {})
            curated.setdefault("records", []).append({
                "classAbbreviation": proposed.get("classAbbreviation"),
                "lapTime": proposed.get("lapTime"),
                "driverName": proposed.get("driverName"),
                "marque": proposed.get("marque"),
                "date": proposed.get("date"),
                "addedAt": _utc_now_iso(),
                "source": "speedhive",
            })
        curated["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        save_curated(p, curated)

    payload["candidates"] = remaining
    save_candidates(p, payload)
    return {"approved": len(to_approve), "skipped": len(remaining)}


def delete_curated_record(p, identity):
    """Remove a record from the curated list by identity.

    Manually-added records are permanently deleted -- there's nothing a scan
    could ever regenerate for them. Everything else is grounded in real
    announcer data, so a full copy is kept on the reject list: not just to
    block it from reappearing, but so `restore_rejected_record` can put it
    straight back later. Records are historical (fastest *as of when set*),
    so a scan re-deriving a deleted one isn't reliable -- an old record is
    usually slower than whatever's fastest for that class *now*.

    Returns {"found": False} or {"found": True, "permanent": bool, "record": dict}.
    """
    curated = load_curated(p)
    target = _find_by_identity(curated.get("records", []), identity)
    if target is None:
        return {"found": False}

    curated["records"] = [r for r in curated.get("records", []) if r is not target]
    curated["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    save_curated(p, curated)

    if target.get("source") == "manual":
        return {"found": True, "permanent": True, "record": target}

    rejected_payload = load_rejected(p)
    rejected_payload.setdefault("rejected", []).append({
        "classAbbreviation": identity[0],
        "lapTime": identity[1],
        "driverName": identity[2],
        "date": identity[3],
        "rejected_at": _utc_now_iso(),
        "reason": "deleted_from_curated",
        "record": dict(target),
    })
    save_rejected(p, rejected_payload)
    return {"found": True, "permanent": False, "record": target}


def restore_rejected_record(org_id, storage, track_records_root, identity):
    """Undo a rejection/deletion by identity.

    If the rejected entry carries a full `record` (it was a deleted curated
    record), put that exact record straight back into curated -- a literal
    undo, not run through the scan/diff "is this a new record" gate, which
    only makes sense for genuinely new laps, not for reversing a delete.

    If it doesn't carry a `record` (it was a rejected review-queue candidate,
    never curated), there's nothing to directly restore -- unblock it and let
    a fresh scan decide whether it still qualifies as a candidate.

    Returns a dict describing the outcome for the caller to build a notice from:
    {"found": False}, or {"found": True, "restored_to_curated": bool, ...}.
    """
    p = paths_for_org(track_records_root, org_id)
    rejected_payload = load_rejected(p)
    all_rejected = rejected_payload.get("rejected", [])
    restored_entry = _find_by_identity(all_rejected, identity)
    if restored_entry is None:
        return {"found": False}

    rejected_payload["rejected"] = [r for r in all_rejected if r is not restored_entry]
    save_rejected(p, rejected_payload)

    if restored_entry.get("record"):
        curated = load_curated(p)
        curated.setdefault("records", []).append(restored_entry["record"])
        curated["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        save_curated(p, curated)
        return {"found": True, "restored_to_curated": True}

    try:
        run_sync_and_diff(org_id, storage, track_records_root)
        reappeared = any(
            c.get("proposed", {}).get("classAbbreviation") == identity[0]
            and c.get("proposed", {}).get("lapTime") == identity[1]
            and c.get("proposed", {}).get("driverName") == identity[2]
            for c in load_candidates(p).get("candidates", [])
        )
        return {"found": True, "restored_to_curated": False, "reappeared": reappeared}
    except Exception as exc:
        return {"found": True, "restored_to_curated": False, "reappeared": None, "rescan_error": str(exc)}


_online_status_cache = {}


def get_cache_status(org_id, storage, track_records_root, client=None):
    """Freshness info for the Speedhive cache -- queries Speedhive dynamically if client is provided."""
    p = paths_for_org(track_records_root, org_id)

    candidates_payload = load_candidates(p)
    pending_candidates = len(candidates_payload.get("candidates", []))

    stale_after_hours = DEFAULT_STALE_AFTER_HOURS

    last_refresh_at = None
    age_hours = None
    needs_sync_local = True

    try:
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

    if client:
        try:
            # Query Speedhive's latest 5 events for this organization
            online_events = client.get_events(org_id, limit=5) or []
            if online_events:
                cached_events = storage.get_events(org_id).payload or []
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


def run_sync_and_diff(org_id, storage, track_records_root, progress_cb=None, parser=None, bulk_parser=None):
    """Extract + normalize + diff for one org, against the already-synced cache
    in storage. Does NOT perform the Speedhive sync itself -- callers are
    responsible for refreshing storage first if needed (e.g. via the generic
    refresh_org_cache machinery). Returns a summary dict.

    `parser`/`bulk_parser` are passed through to storage.get_track_records() --
    pass an LLM-based parser to use instead of the default regex parser.
    `bulk_parser` takes priority when both are given.
    """
    def report(phase):
        if progress_cb:
            progress_cb(phase)

    p = paths_for_org(track_records_root, org_id)
    if not storage.org_has_sessions(org_id):
        raise RuntimeError(f"No cache for org {org_id}; sync the org first.")

    # Cache announcement parse results (record-or-None) across scans so only
    # genuinely new announcements are ever sent through the LLM/regex parser --
    # re-diffing already-seen ones (e.g. after restoring a rejected candidate)
    # still works exactly as before since cached results still feed raw_records.
    report("Extracting announcer-flagged records")
    engine = "llm" if bulk_parser is not None else "regex"
    cache_doc = load_parse_cache(p)
    parse_cache = cache_doc.get("cache", {}) if cache_doc.get("engine") == engine else {}
    new_parse_results = {}
    raw_records = storage.get_track_records(
        org_id,
        parser=parser,
        bulk_parser=bulk_parser,
        parse_cache=parse_cache,
        on_parsed=lambda key, result: new_parse_results.__setitem__(key, result),
    )

    report("Normalizing and diffing against curated records")
    alias_map = load_json(p["alias_map"], {"aliases": {}, "always_review": []})
    curated = load_curated(p)
    rejected_rows = load_rejected(p).get("rejected", [])
    rejected_keys = {
        rejected_key(r.get("classAbbreviation"), r.get("lapTime"), r.get("driverName"), r.get("date"))
        for r in rejected_rows
    }

    curated_fastest = build_curated_fastest_index(curated)
    # For "is this raw record already represented" purposes, identity is
    # (class, lap time, driver) -- NOT date. The same announcement can end up
    # with different computed dates depending on where the date comes from
    # (the announcement's own timestamp vs. an event's overall start date --
    # older imports used the latter), so requiring an exact date match let the
    # same real record look "new" and get proposed as a duplicate.
    curated_ldc = {
        make_ldc(r.get("classAbbreviation"), r.get("lapTime"), r.get("driverName"))
        for r in curated.get("records", [])
    }
    rejected_ldc = {
        make_ldc(r.get("classAbbreviation"), r.get("lapTime"), r.get("driverName"))
        for r in rejected_rows
    }

    auto_rejected = []
    seen_flagged_keys = set()
    candidates = []
    seen_candidate_ldc = set()

    # Records are a historical ledger, not "whoever is fastest right now" --
    # every announcer-flagged lap that set a record at the time it happened
    # belongs in curated eventually. So each raw row is checked individually
    # against what's already curated/rejected; a row is a candidate whenever
    # it isn't represented yet, regardless of whether some *other*, faster
    # row already exists for the same class. (Comparing only the single
    # fastest raw row per class against the current curated best -- the old
    # behavior -- meant any non-fastest historical row could never surface:
    # deleting it left no way for a scan to ever bring it back.)
    for row in raw_records:
        status, resolved = normalize_classification(row.get("classification"), alias_map)
        ts = row.get("timestamp")
        date_str = str(ts)[:10] if ts else None

        # Anything the parser itself flagged as unreliable -- an
        # unrecognized/ambiguous classification token, or (for the LLM
        # parser) a low-confidence extraction -- skips human review
        # entirely and goes straight to rejected. It's still visible and
        # restorable from the Rejected tab if that turns out to be wrong;
        # it just isn't presented as something to decide on.
        if status != "ok" or row.get("llm_uncertain"):
            key = rejected_key(row.get("classification"), row.get("lap_time"), row.get("driver"), date_str)
            if key in rejected_keys or key in seen_flagged_keys:
                continue
            seen_flagged_keys.add(key)
            rejected_keys.add(key)
            auto_rejected.append({
                "classAbbreviation": row.get("classification"),
                "lapTime": row.get("lap_time"),
                "driverName": row.get("driver"),
                "marque": row.get("marque"),
                "date": date_str,
                "rejected_at": _utc_now_iso(),
                "reason": status if status != "ok" else "llm_uncertain",
            })
            continue

        secs = row.get("lap_time_seconds")
        if secs is None:
            secs = lap_time_to_seconds(row.get("lap_time"))
        if secs is None:
            continue

        proposed = {
            "classAbbreviation": resolved,
            "lapTime": row.get("lap_time"),
            "driverName": row.get("driver"),
            "marque": row.get("marque"),
            "date": date_str,
        }
        ldc = make_ldc(resolved, proposed["lapTime"], proposed["driverName"])
        if ldc in curated_ldc or ldc in rejected_ldc or ldc in seen_candidate_ldc:
            continue
        seen_candidate_ldc.add(ldc)

        current = curated_fastest.get(resolved)
        current_public = None
        if current is not None:
            current_public = {k: current[k] for k in ("classAbbreviation", "lapTime", "driverName", "marque", "date")}

        candidates.append({
            "action": "new_record",
            "classAbbreviation": resolved,
            "current": current_public,
            "proposed": proposed,
            "raw": {
                "event_name": row.get("event_name"),
                "session_name": row.get("session_name"),
                "text": row.get("text"),
            },
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "org_id": org_id,
        "candidates": candidates,
    }
    save_candidates(p, payload)

    if auto_rejected:
        rejected_payload = load_rejected(p)
        rejected_payload.setdefault("rejected", []).extend(auto_rejected)
        save_rejected(p, rejected_payload)

    # Persist newly-parsed announcements last, only after candidates/rejected
    # have been successfully saved -- if anything above raised, nothing here
    # gets marked cached, so a retry just redoes the same (small) amount of
    # work rather than silently losing a result.
    if new_parse_results:
        parse_cache.update(new_parse_results)
        save_parse_cache(p, {"engine": engine, "cache": parse_cache})

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    save_ndjson(p["history"] / f"candidates_{stamp}.ndjson", payload, "candidates")

    new_count = len(candidates)
    unmapped_count = len(auto_rejected)

    if candidates:
        notify_gotify(
            f"Track records: new candidates for org {org_id}",
            f"{new_count} new record candidate(s) waiting for review at /org/{org_id}/track-records/review"
            + (f" ({unmapped_count} additional record(s) auto-rejected as unsure -- see the Rejected tab)." if unmapped_count else "."),
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
    storage,
    track_records_root,
    *,
    mode: str = "incremental",
    force: bool = False,
    max_events=None,
    recent_backfill_events: int = 20,
    cleanup_on_full: bool = True,
    progress_cb=None,
    parser=None,
    bulk_parser=None,
):
    """Refresh the org cache if needed, then run the track-record scan.

    This is the single orchestration entrypoint used by the UI and CLI when
    they want the full update flow instead of only diffing an already-synced
    cache. `parser`/`bulk_parser` are passed through to run_sync_and_diff().
    """
    def report(phase):
        if progress_cb:
            progress_cb(phase)

    status = get_cache_status(org_id, storage, track_records_root, client=client)
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
            storage=storage,
        )
    else:
        age_str = f"{status['age_hours']:.1f}h" if status.get("age_hours") is not None else "unknown age"
        report(f"Speedhive cache is fresh ({age_str} old), skipping refresh")

    report("Scanning cached Speedhive data for track records")
    scan_result = run_sync_and_diff(org_id, storage, track_records_root, progress_cb=progress_cb, parser=parser, bulk_parser=bulk_parser)
    return {
        "status": status,
        "refresh": refresh_result,
        "scan": scan_result,
        "refresh_ran": refresh_result is not None,
    }
