#!/usr/bin/env python3
"""Extract all race laps for a driver from processed offline output and write a report file.

This script uses ONLY offline artifacts under `output/` and `output/full_dump/`.
It does not call any network/API.

Outputs a JSON file in `output/` named `driver_laps_<org>_<sanitized_name>.json` with:
- driver_query: original query
- matched_score: best fuzzy score
- matched_names: list of matched name variants
- total_laps, mean, median, stdev, cv
- laps: list of lap objects (lap seconds + session/event metadata)
- session_keys: list of session-position keys included

Run example:
    python3 examples/fun/extract_driver_laps.py --org 30476 --driver "Nathan Crosty"
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, List
import difflib
from speedhive_tools.utils.common import open_ndjson, extract_iso_date, load_session_map, normalize_name, compute_laps_and_enriched


def is_race_session(session_raw: Dict) -> bool:
    if not isinstance(session_raw, dict):
        return False
    t = session_raw.get("type") or session_raw.get("sessionType") or session_raw.get("raceType")
    if isinstance(t, str) and t.lower() == "race":
        return True
    name = session_raw.get("name") or session_raw.get("sessionName") or ""
    if isinstance(name, str) and "race" in name.lower():
        return True
    for k in ("classification", "class", "classificationName", "className"):
        v = session_raw.get(k)
        if isinstance(v, str) and "race" in v.lower():
            return True
    return False


# Deprecated on-disk artifacts `laps_by_driver` and `consistency_*_enriched.json`
# were previously created by a legacy processing step. We now compute those maps
# on-demand from the raw export located under `dump_dir/<org>`.


def gather_driver_keys(enriched: Dict[str, Dict], query: str, threshold: float = 0.85) -> List[str]:
    """Return list of driver_keys (e.g. session123_pos4) whose `name` fuzzy-matches the query.
    Use SequenceMatcher ratio with normalized names and threshold.
    """
    qn = normalize_name(query)
    matched = []
    best_score = 0.0
    # first, find best representative name
    names = set(v.get("name") for v in enriched.values() if v.get("name"))
    best_name = None
    for n in names:
        try:
            score = difflib.SequenceMatcher(None, qn, normalize_name(n)).ratio()
        except Exception:
            score = 0.0
        if score > best_score:
            best_score = score
            best_name = n
    if best_score >= threshold and best_name is not None:
        # include any enriched entries whose normalized name closely matches best_name
        bn_norm = normalize_name(best_name)
        for key, v in enriched.items():
            nm = v.get("name")
            if not nm:
                continue
            try:
                if difflib.SequenceMatcher(None, normalize_name(nm), bn_norm).ratio() >= threshold:
                    matched.append(key)
            except Exception:
                continue
    else:
        # fall back: collect any entries where normalized name similarity to query >= threshold
        for key, v in enriched.items():
            nm = v.get("name")
            if not nm:
                continue
            try:
                if difflib.SequenceMatcher(None, qn, normalize_name(nm)).ratio() >= threshold:
                    matched.append(key)
            except Exception:
                continue
    return matched


def compute_stats(laps: List[float]) -> Dict[str, Any]:
    n = len(laps)
    if n == 0:
        return {"lap_count": 0, "mean": None, "median": None, "stdev": None, "cv": None}
    m = mean(laps)
    med = median(laps)
    sd = stdev(laps) if n > 1 else 0.0
    cv = sd / m if m else None
    return {"lap_count": n, "mean": m, "median": med, "stdev": sd, "cv": cv}


def sanitize_name_for_file(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]", "_", name)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")[:200]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--org", type=int, required=True)
    p.add_argument("--driver", "--name", dest="driver", required=True)
    p.add_argument("--driver-keys", type=str, default=None, help="Comma-separated driver_key values to extract (skip fuzzy matching)")
    p.add_argument("--dump-dir", type=Path, default=Path("output"))
    p.add_argument("--out-dir", type=Path, default=Path("output"))
    p.add_argument("--threshold", type=float, default=0.85)
    p.add_argument("--min-laps", type=int, default=0, help="Minimum lap count for candidate drivers (uses laps_index if available)")
    args = p.parse_args(argv)

    org = args.org
    query = args.driver
    dump_dir = args.dump_dir
    out_dir = args.out_dir

    # Compute laps_by_driver and enriched maps on-demand from the raw dump
    laps_map, enriched = compute_laps_and_enriched(dump_dir, org)
    session_map = load_session_map(dump_dir, org)

    # Optionally load index to pre-filter candidates quickly
    index_path = out_dir / f"laps_index_{org}.json"
    index = None
    if index_path.exists():
        try:
            with open(index_path, "r", encoding="utf8") as fh:
                index = json.load(fh)
        except Exception:
            index = None

    keys = []
    # If driver_keys provided explicitly, use them
    if args.driver_keys:
        keys = [k.strip() for k in args.driver_keys.split(",") if k.strip()]
    else:
        # If an index exists and min_laps specified, prefilter enriched keys
        candidates = list(enriched.keys())
        if index and args.min_laps > 0:
            candidates = [k for k, v in index.items() if (v.get("lap_count") or 0) >= args.min_laps]
        # run fuzzy matching only on candidates
        sub_enriched = {k: enriched[k] for k in candidates if k in enriched}
        keys = gather_driver_keys(sub_enriched, query, threshold=args.threshold)
    if not keys:
        print(f"No driver keys matched query '{query}' (threshold {args.threshold})")
        return 1

    # collect laps only for session_keys that are races
    selected_laps_details: List[Dict[str, Any]] = []
    included_session_keys = []
    for key in keys:
        v = enriched.get(key) or {}
        session_keys = v.get("session_keys") or []
        # check if this driver_key's session_keys include race sessions
        include_key = False
        sid_from_key = None
        for sk in session_keys:
            if sk.startswith("session") and "_pos" in sk:
                try:
                    sid = sk.split("_")[0].replace("session", "")
                    raw = session_map.get(sid)
                    if raw and is_race_session(raw):
                        include_key = True
                        sid_from_key = sid
                        break
                except Exception:
                    pass
        if not include_key:
            continue
        # fetch laps from laps_map
        laps = laps_map.get(key) or []
        if not laps:
            continue
        # determine session id from driver key if possible (pattern session{sid}_pos{p})
        m = None
        import re as _re
        m = _re.match(r"session(\d+)_pos(\d+)", key)
        sid = None
        if m:
            sid = m.group(1)

        # lookup session and event info
        session_raw = session_map.get(sid) if sid else None
        event_id = None
        event_name = None
        session_name = None
        session_date = None
        event_date = None
        if session_raw:
            # session name
            session_name = session_raw.get("name") or session_raw.get("sessionName") or (session_raw.get("raw") or {}).get("name")
            # event id/name can be in different places
            event_id = session_raw.get("event_id") or session_raw.get("eventId") or (session_raw.get("event") or {}).get("id") or (session_raw.get("raw") or {}).get("eventId")
            event_name = session_raw.get("event_name") or session_raw.get("eventName") or (session_raw.get("event") or {}).get("name") or (session_raw.get("raw") or {}).get("eventName")
            # session/event dates
            try:
                session_date = extract_iso_date(session_raw)
            except Exception:
                session_date = None
            try:
                event_raw = session_raw.get("event") or (session_raw.get("raw") or {}).get("event") or {}
                event_date = extract_iso_date(event_raw) or extract_iso_date(session_raw)
            except Exception:
                event_date = extract_iso_date(session_raw)

        for lap in laps:
            try:
                lap_v = float(lap)
            except Exception:
                continue
            selected_laps_details.append({
                "lap": lap_v,
                "driver_key": key,
                "session_id": sid,
                "session_name": session_name,
                "session_date": session_date,
                "event_id": event_id,
                "event_name": event_name,
                "event_date": event_date,
            })
        included_session_keys.append(key)

    if not selected_laps_details:
        print(f"No race laps found for query '{query}'")
        return 1

    # compute stats from raw pooled lap arrays
    lap_values = [d["lap"] for d in selected_laps_details]
    stats = compute_stats(lap_values)

    matched_names = [n for n in list({(enriched.get(k) or {}).get("name") for k in keys if (enriched.get(k) or {}).get("name")}) if n]
    best_score = 0.0
    qn = normalize_name(query)
    for n in matched_names:
        try:
            sc = difflib.SequenceMatcher(None, qn, normalize_name(n)).ratio()
        except Exception:
            sc = 0.0
        if sc > best_score:
            best_score = sc

    # write output file
    rep_name = matched_names[0] if matched_names else query
    fname = out_dir / f"driver_laps_{org}_{sanitize_name_for_file(rep_name)}.json"
    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "driver_query": query,
        "matched_names": matched_names,
        "matched_score": best_score,
        "session_keys": included_session_keys,
        "report": stats,
        "laps": selected_laps_details,  # include lap dicts with session/event info
        "lap_count_total": len(lap_values),
    }
    with open(fname, "w", encoding="utf8") as fh:
        json.dump(out, fh, indent=2)

    print(f"Wrote {fname} with {len(lap_values)} laps. CV={stats.get('cv')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
