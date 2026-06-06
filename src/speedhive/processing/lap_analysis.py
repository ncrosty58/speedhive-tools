#!/usr/bin/env python3
"""Lap analysis utilities: NDJSON reading, time parsing, track record extraction."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from speedhive.processing.ndjson import open_ndjson


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


def compute_laps_and_enriched(dump_dir: Path, org: int):
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

    session_pos_map = {sid: _build_pos_name_map(raw) for sid, raw in sessions.items()}

    results_path = dump / "results.ndjson.gz"
    if not results_path.exists():
        results_path = dump / "results.ndjson"
    if results_path.exists():
        for obj in open_ndjson(results_path):
            sid = obj.get("session_id") or obj.get("sessionId")
            if sid is None:
                continue
            sid = str(int(sid))
            rows = obj.get("results") or obj.get("rows") or []
            if not isinstance(rows, list):
                continue
            mapping = {}
            for r in rows:
                try:
                    pos = r.get("position") or r.get("pos")
                    name = r.get("name") or (r.get("competitor") or {}).get("name")
                    if pos is not None and name:
                        mapping[int(pos)] = name
                except Exception:
                    continue
            existing = session_pos_map.get(sid, {})
            merged = {**existing, **mapping}
            session_pos_map[sid] = merged

    laps_by_driver = defaultdict(list)
    if laps_path.exists():
        for entry in open_ndjson(laps_path):
            sid = entry.get("session_id") or entry.get("sessionId") or entry.get("session")
            if sid is None:
                continue
            sid = str(int(sid))
            rows = entry.get("rows") or entry.get("rows_list") or entry.get("laps") or []
            if not isinstance(rows, list):
                continue
            pos_map = session_pos_map.get(sid, {})
            for row in rows:
                # nested laps lists
                if isinstance(row.get("laps"), list):
                    parent = row
                    for lap in parent.get("laps", []):
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
    import statistics
    for key, laps in laps_by_driver.items():
        if not isinstance(laps, list) or not laps:
            continue
        n = len(laps)
        m = statistics.mean(laps)
        med = statistics.median(laps)
        sd = statistics.stdev(laps) if n > 1 else 0.0
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
        }

    return dict(laps_by_driver), enriched


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
