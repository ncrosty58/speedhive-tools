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