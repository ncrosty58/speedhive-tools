#!/usr/bin/env python3
"""Common utilities for processing Speedhive data.

Shared functions for NDJSON reading, date extraction, session mapping, etc.
"""
from __future__ import annotations

import gzip
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


def open_ndjson(path: Path) -> Iterator[Dict[str, Any]]:
    """Open and yield NDJSON objects from a file (handles .gz)."""
    if not path.exists():
        return
    fh = gzip.open(path, "rt", encoding="utf8") if path.suffix == ".gz" or path.name.endswith(".gz") else open(path, "r", encoding="utf8")
    for ln in fh:
        ln = ln.strip()
        if not ln:
            continue
        try:
            yield json.loads(ln)
        except Exception:
            continue
    fh.close()


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
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s.strip()


def compute_laps_and_enriched(dump_dir: Path, org: int):
    """Compute laps_by_driver and enriched mappings from an export directory.

    Returns a tuple (laps_by_driver: Dict[str, List[float]], enriched: Dict[str, Dict])
    that mirrors the artifacts previously produced by the legacy processing step.
    The function is defensive about gzipped/plain NDJSON filenames.
    """
    from collections import defaultdict
    import re

    dump = dump_dir / str(org)
    # locate session and laps files (gz or plain)
    sess_path = dump / "sessions.ndjson.gz"
    if not sess_path.exists():
        sess_path = dump / "sessions.ndjson"
    laps_path = dump / "laps.ndjson.gz"
    if not laps_path.exists():
        laps_path = dump / "laps.ndjson"

    # build sessions mapping
    sessions = {}
    if sess_path.exists():
        for obj in open_ndjson(sess_path):
            sid = obj.get("session_id") or obj.get("sessionId") or (obj.get("raw") or {}).get("id")
            if sid is None:
                continue
            sid = str(int(sid))
            sessions[sid] = obj.get("raw") or obj

    def build_pos_name_map(session_raw: dict):
        mapping = {}
        if not isinstance(session_raw, dict):
            return mapping
        candidates = []
        if isinstance(session_raw.get("results"), list):
            candidates.extend(session_raw.get("results") or [])
        if isinstance(session_raw.get("positions"), list):
            candidates.extend(session_raw.get("positions") or [])
        for k in ("groups", "classifications"):
            if isinstance(session_raw.get(k), list):
                for g in session_raw.get(k, []) or []:
                    if isinstance(g, dict) and isinstance(g.get("results"), list):
                        candidates.extend(g.get("results", []))
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

    # build per-session pos maps
    session_pos_map = {sid: build_pos_name_map(raw) for sid, raw in sessions.items()}

    # merge results.ndjson mappings if present
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
                    for lap in row.get("laps", []):
                        t = None
                        for tf in ("lapTime", "lap_time", "time", "lapSeconds", "seconds"):
                            if tf in lap:
                                t = parse_time_value(lap.get(tf))
                                if t is not None:
                                    break
                        if t is None:
                            continue
                        # assign key
                        key = None
                        for fld in ("position", "pos", "result_position", "start_position"):
                            if fld in parent and parent.get(fld) is not None:
                                try:
                                    p = int(parent.get(fld))
                                    key = f"session{sid}_pos{p}"
                                except Exception:
                                    pass
                        if key is None:
                            candidate_name = None
                            for nf in ("competitor", "participant", "driver", "name"):
                                v = parent.get(nf)
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
                # assign key by position or name
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
                laps_by_driver[key].append(t)

    # build enriched
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