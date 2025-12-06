
"""
utils.py
Utility helpers for Speedhive tools:
- Time parsing/formatting (lap times)
- Date parsing/formatting
- Announcement parsing (e.g., "New Track Record")
- Data normalization helpers
- JSON/CSV I/O helpers
- Basic iterable utilities
- Lightweight pagination helper (offset/limit style)

These are intentionally generic so they can be used by both client code
and by example scripts or downstream consumers.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Type, TypeVar

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Types
# ------------------------------------------------------------------------------

T = TypeVar("T")

# ------------------------------------------------------------------------------
# Time & Date Helpers
# ------------------------------------------------------------------------------

_LAP_TIME_RX = re.compile(
    r"""
    ^\s*
    (?:
        (?P<hours>\d+):(?P<minutes>[0-5]?\d):(?P<seconds>\d{1,2}(?:\.\d+)?)
        |
        (?P<minutes_only>[0-5]?\d):(?P<seconds_only>\d{1,2}(?:\.\d+)?)
        |
        (?P<seconds_flat>\d+(?:\.\d+)?)
    )
    \s*$
    """,
    re.VERBOSE,
)


def parse_lap_time_to_seconds(value: str) -> float:
    """
    Parse lap time strings into total seconds (float).

    Accepted forms:
    - "MM:SS.sss"      -> e.g., "1:01.861"
    - "HH:MM:SS.sss"   -> e.g., "0:01:01.861" or "01:02:03.456"
    - "SS.sss"         -> e.g., "61.861"

    Returns
    -------
    float
        Total seconds.

    Raises
    ------
    ValueError
        If the format cannot be parsed.
    """
    if value is None:
        raise ValueError("Lap time cannot be None")

    m = _LAP_TIME_RX.match(value.strip())
    if not m:
        raise ValueError(f"Unrecognized lap time format: {value!r}")

    gd = m.groupdict()

    if gd.get("hours") is not None:
        hours = int(gd["hours"])
        minutes = int(gd["minutes"])
        seconds = float(gd["seconds"])
        return hours * 3600 + minutes * 60 + seconds

    if gd.get("minutes_only") is not None:
        minutes = int(gd["minutes_only"])
        seconds = float(gd["seconds_only"])
        return minutes * 60 + seconds

    return float(gd["seconds_flat"])


def format_seconds_to_lap_time(seconds: float) -> str:
    """
    Format total seconds into "M:SS.sss" (drops hours; suitable for most lap times).

    Examples
    --------
    61.861 -> "1:01.861"
    125.0  -> "2:05.000"
    """
    if seconds < 0:
        raise ValueError("seconds must be non-negative")

    minutes, sec = divmod(seconds, 60.0)
    # Always show minutes as integer, seconds with 2 digits plus millisecond precision
    return f"{int(minutes)}:{sec:06.3f}"


# Common date patterns seen in Speedhive-like data
_DATE_PATTERNS = [
    "%Y-%m-%d",            # 2009-05-10
    "%Y-%m-%dT%H:%M:%SZ",  # 2009-05-10T14:30:00Z
    "%Y-%m-%dT%H:%M:%S",   # 2009-05-10T14:30:00
    "%m/%d/%Y",            # 05/10/2009
    "%d-%m-%Y",            # 10-05-2009
]


def parse_date(value: str, *, tz_aware: bool = False) -> datetime:
    """
    Parse a date/time string into a datetime.

    Parameters
    ----------
    value : str
        Date or datetime string.
    tz_aware : bool
        If True, attach UTC timezone when none is present.

    Returns
    -------
    datetime

    Raises
    ------
    ValueError
        If the value cannot be parsed by known patterns.
    """
    v = value.strip()
    # Try ISO first
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if tz_aware and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    # Try known patterns
    for fmt in _DATE_PATTERNS:
        try:
            dt = datetime.strptime(v, fmt)
            if tz_aware and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue

    raise ValueError(f"Unrecognized date format: {value!r}")


def format_date_iso(dt: datetime) -> str:
    """
    Format datetime as ISO 8601 string (UTC normalized if tz-aware).
    """
    if dt.tzinfo:
        return dt.astimezone(timezone.utc).isoformat()
    return dt.isoformat()


# ------------------------------------------------------------------------------
# Text Normalization & Parsing
# ------------------------------------------------------------------------------

_WHITESPACE_RX = re.compile(r"\s+", re.UNICODE)


def normalize_space(text: str) -> str:
    """
    Collapse multiple whitespace to single spaces and trim.
    """
    return _WHITESPACE_RX.sub(" ", text or "").strip()


_SANITIZE_RX = re.compile(r"[\u200B-\u200D\uFEFF]")  # zero-width chars


def sanitize_text(text: str) -> str:
    """
    Remove zero-width characters and normalize spaces.
    """
    return normalize_space(_SANITIZE_RX.sub("", text or ""))


# Example announcement:
# "New Track Record – FA – 1:01.861 – J. Lewis Cooper, Jr – Swift 01 4A – 2009-05-10"
_ANNOUNCEMENT_RX = re.compile(
    r"""
    ^\s*
    (?P<prefix>New\s+Track\s+Record)\s*[–-]\s*
    (?P<class>[A-Za-z0-9+/._\- ]+)\s*[–-]\s*
    (?P<lap>[0-9:\.]+)\s*[–-]\s*
    (?P<driver>[^–-]+?)\s*[–-]\s*
    (?P<marque>[^–-]+?)\s*[–-]\s*
    (?P<date>[\d]{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})
    \s*$
    """,
    re.VERBOSE,
)


def try_parse_track_record_announcement(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to parse a 'New Track Record' announcement into structured fields.

    Returns
    -------
    dict | None
        {
            "classAbbreviation": str,
            "lapTime": str,
            "driverName": str,
            "marque": str,
            "date": str,
        }
        Or None if the text doesn't match the expected pattern.
    """
    clean = sanitize_text(text)
    m = _ANNOUNCEMENT_RX.match(clean)
    if not m:
        return None

    gd = m.groupdict()
    # Normalize keys to match your JSON schema
    result = {
        "classAbbreviation": normalize_space(gd["class"]),
        "lapTime": gd["lap"],
        "driverName": normalize_space(gd["driver"]),
        "marque": normalize_space(gd["marque"]),
        "date": normalize_space(gd["date"]),
    }
    return result


# ------------------------------------------------------------------------------
# Data Normalization Helpers
# ------------------------------------------------------------------------------

def maybe_float(v: Any, default: Optional[float] = None) -> Optional[float]:
    """
    Convert value to float if possible, else return default.
    """
    try:
        return float(v)
    except Exception:
        return default


def maybe_int(v: Any, default: Optional[int] = None) -> Optional[int]:
    """
    Convert value to int if possible, else return default.
    """
    try:
        return int(v)
    except Exception:
        return default


def safe_get(d: Dict[str, Any], path: Sequence[str], default: Any = None) -> Any:
    """
    Safely navigate nested dicts using a list of keys.

    Example
    -------
    safe_get(data, ["events", "items", 0, "name"])
    """
    cur: Any = d
    for key in path:
        try:
            if isinstance(key, int) and isinstance(cur, list):
                cur = cur[key]
            elif isinstance(cur, dict):
                cur = cur.get(key)
            else:
                return default
        except Exception:
            return default
        if cur is None:
            return default
    return cur


def flatten(nested: Iterable[Iterable[T]]) -> List[T]:
    """
    Flatten a 2D iterable into a list.
    """
    out: List[T] = []
    for sub in nested:
        out.extend(sub)
    return out


# ------------------------------------------------------------------------------
# I/O Helpers
# ------------------------------------------------------------------------------

def ensure_dir(path: str) -> None:
    """
    Ensure the directory for the given file path exists.
    """
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def write_json(obj: Any, file_path: str, *, indent: int = 2) -> None:
    """
    Write an object to JSON file.
    """
    ensure_dir(file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False)


def read_json(file_path: str) -> Any:
    """
    Read a JSON file and return the parsed object.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_csv(rows: List[Dict[str, Any]], file_path: str, *, headers: Optional[List[str]] = None) -> None:
    """
    Write a list of dictionaries to CSV. Headers are inferred if not provided.
    """
    ensure_dir(file_path)
    if not rows:
        # Still create a file—either with given headers or empty
        hdr = headers or []
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=hdr)
            if hdr:
                writer.writeheader()
        return

    if headers is None:
        headers = sorted({k for r in rows for k in r.keys()})

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ------------------------------------------------------------------------------
# Iterable Utilities
# ------------------------------------------------------------------------------

def chunked(iterable: Iterable[T], size: int) -> Iterator[List[T]]:
    """
    Yield lists of size 'size' from 'iterable'.

    Example
    -------
    for batch in chunked(items, 100):
        process(batch)
    """
    if size <= 0:
        raise ValueError("size must be > 0")

    buf: List[T] = []
    for item in iterable:
        buf.append(item)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


def unique_everseen(iterable: Iterable[T]) -> Iterator[T]:
    """
    Yield unique items, preserving order.
    """
    seen = set()
    for item in iterable:
        if item not in seen:
            seen.add(item)
            yield item


# ------------------------------------------------------------------------------
# Pagination Helpers (offset/limit style)
# ------------------------------------------------------------------------------

def paginate_offset_limit(
    fetch_page: Callable[[int, int], Dict[str, Any]],
    item_key: str,
    *,
    start_offset: int = 0,
    limit: int = 100,
    max_items: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    """
    Generic offset/limit paginator.

    Parameters
    ----------
    fetch_page : Callable[[offset, limit], dict]
        Function that takes (offset, limit) and returns a response dict.
    item_key : str
        Key in the response dict containing the list of items.
    start_offset : int
        Starting offset.
    limit : int
        Page size.
    max_items : Optional[int]
        If provided, stop after yielding this many items.

    Yields
    ------
    dict items from the response[item_key]
    """
    offset = start_offset
    yielded = 0

    while True:
        data = fetch_page(offset, limit)
        items = data.get(item_key) or []
        if not items:
            break

        for it in items:
            yield it
            yielded += 1
            if max_items is not None and yielded >= max_items:
                return

        if len(items) < limit:
            # Last page
            break

        offset += limit


# ------------------------------------------------------------------------------
# Convenience: Model constructors
# ------------------------------------------------------------------------------

def to_track_record_dict(
    class_abbreviation: str,
    lap_time_str: str,
    driver_name: str,
    marque: Optional[str],
    date_str: str,
) -> Dict[str, Any]:
    """
    Build a normalized dict suitable for TrackRecord ingestion, preserving original
    string lap_time but also providing numeric seconds for downstream analytics.
    """
    seconds = parse_lap_time_to_seconds(lap_time_str)
    return {
        "classAbbreviation": class_abbreviation,
        "lapTime": lap_time_str,
        "lapTimeSeconds": seconds,
        "driverName": driver_name,
        "marque": marque,
        "date": date_str,
    }
