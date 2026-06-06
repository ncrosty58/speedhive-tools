"""Extract race laps for a fuzzy-matched driver from an offline dump."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, List

from speedhive.processing.process_lap_analysis import (
    compute_laps_and_enriched,
    extract_iso_date,
    load_session_map,
    normalize_name,
)


def is_race_session(session_raw: Dict[str, Any]) -> bool:
    """Best-effort race-session detection across payload variants."""
    if not isinstance(session_raw, dict):
        return False
    kind = session_raw.get("type") or session_raw.get("sessionType") or session_raw.get("raceType")
    if isinstance(kind, str) and kind.lower() == "race":
        return True
    name = session_raw.get("name") or session_raw.get("sessionName") or ""
    if isinstance(name, str) and "race" in name.lower():
        return True
    for key in ("classification", "class", "classificationName", "className"):
        value = session_raw.get(key)
        if isinstance(value, str) and "race" in value.lower():
            return True
    return False


def gather_driver_keys(enriched: Dict[str, Dict[str, Any]], query: str, threshold: float = 0.85) -> List[str]:
    """Return driver-key values whose names fuzzy-match a query."""
    query_norm = normalize_name(query)
    if not query_norm:
        return []

    names = {v.get("name") for v in enriched.values() if isinstance(v, dict) and v.get("name")}
    best_name = None
    best_score = 0.0
    for name in names:
        score = SequenceMatcher(None, query_norm, normalize_name(str(name))).ratio()
        if score > best_score:
            best_score = score
            best_name = str(name)

    matched: List[str] = []
    if best_name and best_score >= threshold:
        target = normalize_name(best_name)
        for key, value in enriched.items():
            name = value.get("name") if isinstance(value, dict) else None
            if not name:
                continue
            if SequenceMatcher(None, normalize_name(str(name)), target).ratio() >= threshold:
                matched.append(key)
        return matched

    for key, value in enriched.items():
        name = value.get("name") if isinstance(value, dict) else None
        if not name:
            continue
        if SequenceMatcher(None, query_norm, normalize_name(str(name))).ratio() >= threshold:
            matched.append(key)
    return matched


def compute_stats(laps: List[float]) -> Dict[str, Any]:
    """Compute summary metrics for a set of lap values in seconds."""
    count = len(laps)
    if count == 0:
        return {"lap_count": 0, "mean": None, "median": None, "stdev": None, "cv": None}
    mean_v = mean(laps)
    median_v = median(laps)
    stdev_v = stdev(laps) if count > 1 else 0.0
    cv_v = (stdev_v / mean_v) if mean_v else None
    return {"lap_count": count, "mean": mean_v, "median": median_v, "stdev": stdev_v, "cv": cv_v}


def sanitize_name_for_file(name: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]", "_", name)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")[:200] or "driver"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extract race laps for a driver from an offline dump")
    parser.add_argument("--org", type=int, required=True)
    parser.add_argument("--driver", "--name", dest="driver", required=True)
    parser.add_argument(
        "--driver-keys",
        type=str,
        default=None,
        help="Comma-separated driver_key values to extract (skips fuzzy matching)",
    )
    parser.add_argument("--dump-dir", type=Path, default=Path("output"))
    parser.add_argument("--out-dir", type=Path, default=Path("output"))
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--min-laps", type=int, default=0)
    args = parser.parse_args(argv)

    laps_map, enriched = compute_laps_and_enriched(args.dump_dir, args.org)
    session_map = load_session_map(args.dump_dir, args.org)

    index = None
    index_path = args.out_dir / f"laps_index_{args.org}.json"
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf8"))
        except Exception:
            index = None

    if args.driver_keys:
        keys = [key.strip() for key in args.driver_keys.split(",") if key.strip()]
    else:
        candidates = list(enriched.keys())
        if index and args.min_laps > 0:
            candidates = [key for key, value in index.items() if (value.get("lap_count") or 0) >= args.min_laps]
        keys = gather_driver_keys({key: enriched[key] for key in candidates if key in enriched}, args.driver, args.threshold)

    if not keys:
        print(f"No driver keys matched query '{args.driver}' (threshold {args.threshold})")
        return 1

    selected_laps_details: List[Dict[str, Any]] = []
    included_session_keys: List[str] = []
    for key in keys:
        info = enriched.get(key) or {}
        session_keys = info.get("session_keys") or []
        include_key = False
        for session_key in session_keys:
            if session_key.startswith("session") and "_pos" in session_key:
                try:
                    session_id = session_key.split("_")[0].replace("session", "")
                    session_raw = session_map.get(session_id)
                    if session_raw and is_race_session(session_raw):
                        include_key = True
                        break
                except Exception:
                    continue
        if not include_key:
            continue

        laps = laps_map.get(key) or []
        if not laps:
            continue

        match = re.match(r"session(\d+)_pos(\d+)", key)
        session_id = match.group(1) if match else None
        session_raw = session_map.get(session_id) if session_id else None
        session_name = None
        session_date = None
        event_id = None
        event_name = None
        event_date = None
        if session_raw:
            session_name = session_raw.get("name") or session_raw.get("sessionName")
            event_id = (
                session_raw.get("event_id")
                or session_raw.get("eventId")
                or (session_raw.get("event") or {}).get("id")
                or (session_raw.get("raw") or {}).get("eventId")
            )
            event_name = (
                session_raw.get("event_name")
                or session_raw.get("eventName")
                or (session_raw.get("event") or {}).get("name")
                or (session_raw.get("raw") or {}).get("eventName")
            )
            session_date = extract_iso_date(session_raw)
            event_raw = session_raw.get("event") or (session_raw.get("raw") or {}).get("event") or {}
            event_date = extract_iso_date(event_raw) or session_date

        for lap in laps:
            try:
                lap_value = float(lap)
            except Exception:
                continue
            selected_laps_details.append(
                {
                    "lap": lap_value,
                    "driver_key": key,
                    "session_id": session_id,
                    "session_name": session_name,
                    "session_date": session_date,
                    "event_id": event_id,
                    "event_name": event_name,
                    "event_date": event_date,
                }
            )
        included_session_keys.append(key)

    if not selected_laps_details:
        print(f"No race laps found for query '{args.driver}'")
        return 1

    lap_values = [row["lap"] for row in selected_laps_details]
    stats = compute_stats(lap_values)
    matched_names = sorted(
        {
            value.get("name")
            for key, value in enriched.items()
            if key in keys and isinstance(value, dict) and value.get("name")
        }
    )

    query_norm = normalize_name(args.driver)
    best_score = 0.0
    for name in matched_names:
        score = SequenceMatcher(None, query_norm, normalize_name(str(name))).ratio()
        if score > best_score:
            best_score = score

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_name = matched_names[0] if matched_names else args.driver
    output_path = args.out_dir / f"driver_laps_{args.org}_{sanitize_name_for_file(report_name)}.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "driver_query": args.driver,
        "matched_names": matched_names,
        "matched_score": best_score,
        "session_keys": included_session_keys,
        "report": stats,
        "laps": selected_laps_details,
        "lap_count_total": len(lap_values),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf8")

    print(f"Wrote {output_path} with {len(lap_values)} laps. CV={stats.get('cv')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
