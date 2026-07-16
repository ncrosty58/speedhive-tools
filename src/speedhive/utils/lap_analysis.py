#!/usr/bin/env python3
"""Lap analysis utilities: NDJSON reading, time parsing, track record parsing."""

from __future__ import annotations

from difflib import SequenceMatcher
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import statistics
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from speedhive.ndjson import open_ndjson

if TYPE_CHECKING:
    from speedhive.storage import SpeedhiveStorage


NORMALIZE_RE = re.compile(r"[^a-z0-9 ]")


def extract_iso_date(raw: Dict[str, Any]) -> Optional[str]:
    """Extract ISO date string from session/event raw dict."""
    if not isinstance(raw, dict):
        return None
    keys = ("startTime", "start_time", "start", "date", "startAt", "startDateTime", "eventDate", "event_date", "scheduledAt")
    for k in keys:
        v = raw.get(k)
        if not v:
            continue
        if isinstance(v, (int, float)):
            ts = float(v)
            if ts > 1e12:
                ts = ts / 1000.0
            try:
                return datetime.utcfromtimestamp(ts).isoformat() + "Z"
            except Exception:
                continue
        if isinstance(v, str):
            return v
    return None


def load_session_map(dump_dir: Path, org: int) -> Dict[str, Dict[str, Any]]:
    """Load session_id -> raw session dict mapping."""
    dump = dump_dir / str(org)
    sess_path = dump / "sessions.ndjson.gz"
    if not sess_path.exists():
        sess_path = dump / "sessions.ndjson"
    mapping: Dict[str, Dict[str, Any]] = {}
    if not sess_path.exists():
        return mapping
    for obj in open_ndjson(sess_path):
        sid = obj.get("session_id") or obj.get("sessionId") or (obj.get("raw") or {}).get("id")
        if sid is None:
            continue
        sid = str(int(sid))
        raw = obj.get("raw") or obj
        mapping[sid] = raw
    return mapping


def parse_time_value(v: Any) -> Optional[float]:
    """Parse a time value (string or numeric) to float seconds."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        pass
    m = re.search(r"(?:(\d+):)?(\d+)(?:\.(\d+))?", s)
    if m:
        mins = m.group(1)
        secs = m.group(2)
        frac = m.group(3) or "0"
        total = (int(mins) * 60 if mins else 0) + int(secs) + float("0." + frac)
        return float(total)
    m2 = re.search(r"(\d+\.\d+|\d+)", s)
    if m2:
        try:
            return float(m2.group(1))
        except Exception:
            return None
    return None


def normalize_name(name: str) -> str:
    """Normalize a name for fuzzy matching."""
    if not name:
        return ""
    s = name.lower()
    s = NORMALIZE_RE.sub("", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def normalize_classification(raw_token, alias_map):
    """Resolve a raw car-class token against an org's curated alias map.

    Returns (status, resolved_abbreviation). status: 'ok' | 'ambiguous'.

    No canonical whitelist is required -- any token is accepted as-is (upper/
    trimmed) unless it's in this org's `always_review` list (for tokens that
    are genuinely ambiguous, e.g. a combined class group that splits into
    multiple record-keeping classes). Shared by track-record curation (the
    human review step is the real safety net for typos/unexpected tokens,
    not a whitelist) and the class-based stats analyzers (analyze_class_pace),
    so both group car classes the same way from one org-maintained alias map.
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


def _build_pos_name_map(session_raw: dict) -> Dict[int, str]:
    mapping = {}
    if not isinstance(session_raw, dict):
        return mapping
    candidates = []
    if isinstance(session_raw.get("results"), list):
        candidates.extend(session_raw["results"])
    if isinstance(session_raw.get("positions"), list):
        candidates.extend(session_raw["positions"])
    for key in ("groups", "classifications"):
        if isinstance(session_raw.get(key), list):
            for g in session_raw[key]:
                if isinstance(g, dict) and isinstance(g.get("results"), list):
                    candidates.extend(g["results"])
    for r in candidates:
        try:
            pos = r.get("position") or r.get("pos")
            comp = r.get("competitor") or {}
            name = r.get("name") or comp.get("name") or r.get("participantName")
            if pos is not None and name:
                mapping[int(pos)] = name
        except Exception:
            continue
    return mapping


def _assign_key(row, sid: str, pos_map: Dict[int, str]) -> str:
    """Helper to build a driver key from a lap row."""
    key = None
    for fld in ("position", "pos", "result_position", "start_position"):
        if fld in row and row.get(fld) is not None:
            try:
                p = int(row.get(fld))
                key = f"session{sid}_pos{p}"
            except Exception:
                pass
    if key is None:
        candidate_name = None
        for nf in ("competitor", "participant", "driver", "name"):
            v = row.get(nf)
            if isinstance(v, dict):
                candidate_name = v.get("name") or v.get("participantName")
            elif isinstance(v, str):
                candidate_name = v
            if candidate_name:
                break
        if candidate_name and pos_map:
            ln = candidate_name.strip().lower()
            for p, n in pos_map.items():
                if n and ln in n.lower():
                    key = f"session{sid}_pos{p}"
    if key is None:
        key = f"session{sid}_unknown"
    return key


def filter_outliers_iqr(laps: List[float]) -> List[float]:
    """Filter out outliers from a list of lap times using the IQR (Interquartile Range) method.

    Laps outside [Q1 - 1.5 * IQR, Q3 + 1.5 * IQR] are considered outliers.
    """
    if len(laps) < 4:
        return laps
    sorted_laps = sorted(laps)
    q = statistics.quantiles(sorted_laps, n=4)
    q1 = q[0]
    q3 = q[2]
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return [lap for lap in laps if lower_bound <= lap <= upper_bound]


def _compute_laps_and_enriched_from_payloads(
    sessions: Dict[str, Dict[str, Any]],
    results_payloads: Dict[str, List[Any]],
    laps_payloads: Dict[str, List[Any]],
    ignore_outliers: bool = False,
):
    session_pos_map = {sid: _build_pos_name_map(raw) for sid, raw in sessions.items()}

    for sid, rows in results_payloads.items():
        if not isinstance(rows, list):
            continue
        mapping = {}
        for r in rows:
            if not isinstance(r, dict):
                continue
            try:
                pos = r.get("position") or r.get("pos")
                name = r.get("name") or (r.get("competitor") or {}).get("name")
                if pos is not None and name:
                    mapping[int(pos)] = name
            except Exception:
                continue
        existing = session_pos_map.get(sid, {})
        session_pos_map[sid] = {**existing, **mapping}

    laps_by_driver = defaultdict(list)
    for sid, rows in laps_payloads.items():
        if not isinstance(rows, list):
            continue
        pos_map = session_pos_map.get(sid, {})
        for row in rows:
            if not isinstance(row, dict):
                continue
            if isinstance(row.get("laps"), list):
                parent = row
                for lap in parent.get("laps", []):
                    # A pit-in/pit-out lap includes time spent off-track in
                    # the pits (sometimes minutes' worth), not racing pace --
                    # pooling it in with green-flag laps skews mean/stdev/CV,
                    # an effect all-time pooling across many laps normally
                    # dilutes into invisibility but that a small single-year
                    # or single-session sample can't absorb.
                    if lap.get("inPit") or lap.get("pit"):
                        continue
                    t = None
                    for tf in ("lapTime", "lap_time", "time", "lapSeconds", "seconds"):
                        if tf in lap:
                            t = parse_time_value(lap.get(tf))
                            if t is not None:
                                break
                    if t is None:
                        continue
                    key = _assign_key(parent, sid, pos_map)
                    laps_by_driver[key].append(t)
                continue

            if row.get("inPit") or row.get("pit"):
                continue

            t = None
            for tf in ("lapTime", "lap_time", "time", "lapSeconds", "seconds"):
                if tf in row:
                    t = parse_time_value(row.get(tf))
                    if t is not None:
                        break
            if t is None:
                continue
            key = _assign_key(row, sid, pos_map)
            laps_by_driver[key].append(t)

    enriched = {}
    for key, laps in laps_by_driver.items():
        if not isinstance(laps, list) or not laps:
            continue
        
        filtered_laps = filter_outliers_iqr(laps) if ignore_outliers else laps
        if not filtered_laps:
            filtered_laps = laps

        n = len(filtered_laps)
        m = statistics.mean(filtered_laps)
        med = statistics.median(filtered_laps)
        sd = statistics.stdev(filtered_laps) if n > 1 else 0.0
        cv = sd / m if m else None
        name = None
        sess_match = re.match(r"session(\d+)_pos(\d+)", key)
        session_keys = [key]
        if sess_match:
            sid = sess_match.group(1)
            pos = int(sess_match.group(2))
            name = session_pos_map.get(sid, {}).get(pos)
        enriched[key] = {
            "name": name,
            "driver_id": key,
            "lap_count": n,
            "mean": m,
            "median": med,
            "stdev": sd,
            "cv": cv,
            "session_keys": session_keys,
            "raw_laps": laps,
            "filtered_laps": filtered_laps,
        }

    return dict(laps_by_driver), enriched


def compute_laps_and_enriched(dump_dir: Path, org: int, ignore_outliers: bool = False):
    """Compute laps_by_driver and enriched mappings from an export directory.

    Returns a tuple (laps_by_driver: Dict[str, List[float]], enriched: Dict[str, Dict])
    """
    dump = dump_dir / str(org)
    sess_path = dump / "sessions.ndjson.gz"
    if not sess_path.exists():
        sess_path = dump / "sessions.ndjson"
    laps_path = dump / "laps.ndjson.gz"
    if not laps_path.exists():
        laps_path = dump / "laps.ndjson"

    sessions = {}
    if sess_path.exists():
        for obj in open_ndjson(sess_path):
            sid = obj.get("session_id") or obj.get("sessionId") or (obj.get("raw") or {}).get("id")
            if sid is None:
                continue
            sid = str(int(sid))
            sessions[sid] = obj.get("raw") or obj

    results_path = dump / "results.ndjson.gz"
    if not results_path.exists():
        results_path = dump / "results.ndjson"
    results_payloads = {}
    if results_path.exists():
        for obj in open_ndjson(results_path):
            sid = obj.get("session_id") or obj.get("sessionId")
            if sid is None:
                continue
            sid = str(int(sid))
            rows = obj.get("results") or obj.get("rows") or []
            if not isinstance(rows, list):
                continue
            results_payloads[sid] = rows

    laps_payloads = {}
    if laps_path.exists():
        for entry in open_ndjson(laps_path):
            sid = entry.get("session_id") or entry.get("sessionId") or entry.get("session")
            if sid is None:
                continue
            sid = str(int(sid))
            rows = entry.get("rows") or entry.get("rows_list") or entry.get("laps") or []
            if not isinstance(rows, list):
                continue
            laps_payloads[sid] = rows

    return _compute_laps_and_enriched_from_payloads(sessions, results_payloads, laps_payloads, ignore_outliers=ignore_outliers)


def compute_laps_and_enriched_from_storage(storage: "SpeedhiveStorage", org: int, ignore_outliers: bool = False):
    """Compute laps_by_driver and enriched mappings from SQLite-backed cache."""
    sessions = storage.load_session_payloads(org)
    results_payloads = storage.load_results_payloads(org)
    laps_payloads = storage.load_laps_payloads(org)
    return _compute_laps_and_enriched_from_payloads(sessions, results_payloads, laps_payloads, ignore_outliers=ignore_outliers)


def parse_track_record_text(text: str) -> Optional[Dict[str, Any]]:
    """Parse announcement text for a track record.

    Returns dict with keys 'lap_time', 'lap_time_seconds', 'classification',
    'driver', 'marque' or None if not a track record.
    """
    pattern = re.compile(
        r"New (?:Track|Class) Record\s*\(([0-9:.]+)\)\s*for\s+([^\s]+)\s+by\s+(.+?)\.?$",
        re.IGNORECASE
    )
    match = pattern.search(text)
    if not match:
        return None
    lap_time_str = match.group(1)
    class_name = match.group(2)
    driver_block = match.group(3).strip()
    low = text.lower()
    if any(x in low for x in ("to be confirmed", "not a track record", "not a class record")):
        return None
    marque = None
    m = re.search(r"^(.+?)\s+in\s+(.+)$", driver_block, re.IGNORECASE)
    if m:
        driver = m.group(1).strip()
        marque = m.group(2).strip().rstrip('.')
    else:
        driver = driver_block
    driver = re.sub(r"^\s*\[\s*\d+\s*\]\s*", "", driver)

    try:
        parts = lap_time_str.split(":")
        if len(parts) == 2:
            lap_seconds = int(parts[0]) * 60 + float(parts[1])
        else:
            lap_seconds = float(lap_time_str)
    except (ValueError, IndexError):
        lap_seconds = None

    return {
        "lap_time": lap_time_str,
        "lap_time_seconds": lap_seconds,
        "classification": class_name,
        "driver": driver,
        "marque": marque,
    }


def format_seconds(seconds: float) -> str:
    """Format float seconds to MM:SS.FFF or SS.FFF representation."""
    if seconds is None:
        return "N/A"
    try:
        minutes = int(seconds // 60)
        secs = seconds % 60
        if minutes > 0:
            return f"{minutes}:{secs:06.3f}".rstrip('0').rstrip('.')
        return f"{secs:.3f}"
    except Exception:
        return "N/A"


def first_non_empty(*values: Any) -> Any:
    """Return first non-empty value from candidates."""
    for value in values:
        if value is None:
            continue
        val_str = str(value).strip()
        if val_str:
            return value
    return None


def session_year(session_raw: Dict) -> Optional[int]:
    """Extract the calendar year a session/event took place in, from
    whichever date-like field is present."""
    raw_date = first_non_empty(
        session_raw.get("startTime"),
        session_raw.get("scheduledStart"),
        session_raw.get("start_date"),
        session_raw.get("date"),
    )
    if not raw_date:
        return None
    match = re.match(r"(\d{4})", str(raw_date))
    return int(match.group(1)) if match else None


def compute_lap_statistics(laps: List[Dict[str, Any]], ignore_outliers: bool = False) -> Dict[str, Any]:
    """Compute consistency, mean, median, stdev, and CV statistics for a list of laps."""
    times = []
    best_time_sec = float('inf')
    best_time_str = "N/A"

    for lap in laps:
        time_str = lap.get("lapTime") or lap.get("lap_time")
        if not time_str:
            continue
        sec = parse_time_value(time_str)
        if sec is not None and sec > 0:
            times.append(sec)
            if sec < best_time_sec:
                best_time_sec = sec
                best_time_str = time_str

    if not times:
        return {
            "lap_count": 0,
            "best_lap": "N/A",
            "mean": "N/A",
            "median": "N/A",
            "stdev": "N/A",
            "cv": "N/A",
            "cv_raw": None,
        }

    filtered_times = filter_outliers_iqr(times) if ignore_outliers else times
    if not filtered_times:
        filtered_times = times

    lap_count = len(filtered_times)
    mean_val = statistics.mean(filtered_times)
    median_val = statistics.median(filtered_times)
    stdev_val = statistics.stdev(filtered_times) if len(filtered_times) > 1 else 0.0
    cv_val = stdev_val / mean_val if mean_val > 0 else 0.0

    return {
        "lap_count": lap_count,
        "best_lap": best_time_str,
        "mean": format_seconds(mean_val),
        "median": format_seconds(median_val),
        "stdev": f"{stdev_val:.3f}",
        "cv": f"{cv_val * 100:.2f}%",
        "cv_raw": cv_val,
    }


def build_lap_chart_from_laps(laps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build lap chart rows from flat lap rows when chart endpoint is unavailable."""
    lap_rows: Dict[int, List[Dict[str, Any]]] = {}
    for lap in laps:
        if not isinstance(lap, dict):
            continue
        lap_no = first_non_empty(lap.get("lapNumber"), lap.get("lap"))
        position = lap.get("position")
        if lap_no is None or position is None:
            continue
        try:
            lap_idx = int(lap_no)
        except Exception:
            lap_idx = -1
        if lap_idx < 0:
            continue
        lap_rows.setdefault(lap_idx, []).append(lap)

    chart_rows = []
    for lap_no in sorted(lap_rows.keys()):
        positions = []
        # Sort by position
        sorted_entries = sorted(
            lap_rows[lap_no],
            key=lambda item: int(item.get("position")) if item.get("position") is not None else 9999
        )
        for entry in sorted_entries:
            label = first_non_empty(entry.get("startNumber"), entry.get("competitorId"))
            if label is None:
                label = f"P{entry.get('position')}"
            positions.append(str(label))
        chart_rows.append({"lapNumber": lap_no, "positions": positions})
    return chart_rows


def normalize_search_text(text: str) -> str:
    """Normalize text for fuzzy matching."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (text or "").lower())).strip()


def name_match_score(query: str, name: str) -> float:
    """Compute fuzzy match score between search query and driver name."""
    q = normalize_search_text(query)
    n = normalize_search_text(name)
    if not q or not n:
        return 0.0
    ratio = SequenceMatcher(None, q, n).ratio()
    token_bonus = 0.0
    q_tokens = [tok for tok in q.split(" ") if tok]
    if q in n:
        token_bonus += 0.25
    if q_tokens and all(tok in n for tok in q_tokens):
        token_bonus += 0.20
    partial_ratio = max((SequenceMatcher(None, tok, n).ratio() for tok in q_tokens), default=0.0)
    return max(ratio, partial_ratio) + token_bonus


def format_gap_display(gap: Any) -> Optional[str]:
    """Format a gap/difference object from classification responses."""
    if not isinstance(gap, dict):
        return None
    laps_behind = gap.get("lapsBehind")
    time_diff = first_non_empty(gap.get("timeDifference"), gap.get("difference"))
    if laps_behind not in (None, "", 0):
        if time_diff and str(time_diff) not in ("00.000", "0", "00:00.000"):
            return f"+{laps_behind} lap(s), {time_diff}"
        return f"+{laps_behind} lap(s)"
    if not time_diff:
        return None
    if str(time_diff) in ("00.000", "0", "00:00.000"):
        return "Leader"
    return f"+{time_diff}" if not str(time_diff).startswith("+") else str(time_diff)


def safe_int(value: Any, default: int = 9999) -> int:
    """Best-effort integer conversion for sorting."""
    try:
        return int(value)
    except Exception:
        return default


def normalize_result_row(
    row: Dict[str, Any],
    available_comp_ids: Optional[set] = None,
    available_start_numbers: Optional[set] = None,
) -> Dict[str, Any]:
    """Normalize result row keys across payload variants for template rendering."""
    competitor = row.get("competitor") if isinstance(row.get("competitor"), dict) else {}
    driver = row.get("driver") if isinstance(row.get("driver"), dict) else {}
    driver_name = first_non_empty(
        row.get("name"),
        row.get("driverName"),
        competitor.get("name"),
        driver.get("name"),
        row.get("participantName"),
    ) or "Unknown Competitor"

    car_name = first_non_empty(
        row.get("car"),
        row.get("vehicle"),
        row.get("marque"),
        competitor.get("car"),
    )
    class_name = first_non_empty(
        row.get("resultClass"),
        row.get("vehicleClass"),
        row.get("classification"),
        row.get("class"),
        competitor.get("class"),
    )
    if car_name and class_name:
        car_class = f"{car_name} / {class_name}"
    else:
        car_class = car_name or class_name or "N/A"

    total_time = first_non_empty(
        row.get("totalTime"),
        row.get("total_time"),
        row.get("time"),
        row.get("elapsedTime"),
        row.get("finishTime"),
    )
    if not total_time:
        total_time = format_gap_display(row.get("difference")) or format_gap_display(row.get("gap")) or "N/A"

    best_lap = first_non_empty(
        row.get("bestLapTime"),
        row.get("best_lap_time"),
        row.get("bestTime"),
        row.get("lapTime"),
    ) or "N/A"

    laps = first_non_empty(
        row.get("laps"),
        row.get("lapCount"),
        row.get("lap_count"),
        row.get("completedLaps"),
        row.get("numberOfLaps"),
    )
    laps_display = laps if laps is not None else "N/A"

    position = first_non_empty(row.get("position"), row.get("pos"))
    competitor_id = first_non_empty(row.get("competitorId"), row.get("id"), competitor.get("id"))
    start_number = first_non_empty(row.get("startNumber"), row.get("transponder"))

    lap_driver_id = None
    action_label = None
    comp_id_ok = competitor_id not in (None, "") and (
        available_comp_ids is None or str(competitor_id) in available_comp_ids
    )
    start_no_ok = start_number not in (None, "") and (
        available_start_numbers is None or str(start_number) in available_start_numbers
    )

    if comp_id_ok:
        lap_driver_id = f"cid:{competitor_id}"
        action_label = "View Laps"
    elif start_no_ok:
        lap_driver_id = f"sn:{start_number}"
        action_label = "View Laps"
    elif position not in (None, ""):
        lap_driver_id = f"pos:{position}"
        action_label = "View Position Trace"

    return {
        "position": position if position is not None else "N/A",
        "position_sort": safe_int(position),
        "driver_name": driver_name,
        "car_class": car_class,
        "total_time_display": total_time,
        "best_lap_display": best_lap,
        "laps_display": laps_display,
        "lap_driver_id": lap_driver_id,
        "action_label": action_label,
    }
