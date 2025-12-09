"""Utilities for parsing track-record announcements.

Centralize the regex and parsing so both the client wrapper and
processors can reuse the same logic and tests.
"""
from __future__ import annotations

import re
from typing import Optional, Dict, Any

from .common import parse_time_value


_RE_TRACK = re.compile(
    r"New (?:Track|Class) Record\s*\(([0-9:.]+)\)\s*for\s+([^\s]+)\s+by\s+(.+?)\.?$",
    re.IGNORECASE,
)


def parse_track_record_text(text: str) -> Optional[Dict[str, Any]]:
    """Parse announcement text and return a dict with parsed fields.

    Returns None if the text doesn't look like a track/class record announcement.
    Fields returned: classification, lap_time (str), lap_time_seconds (float|None), driver, marque
    """
    if not text:
        return None
    m = _RE_TRACK.search(text.strip())
    if not m:
        return None

    lap_time = m.group(1)
    classification = m.group(2)
    driver_block = m.group(3).strip()

    marque = None
    mm = re.search(r"^(.+?)\s+in\s+(.+)$", driver_block, flags=re.IGNORECASE)
    if mm:
        driver_name = mm.group(1).strip()
        marque = mm.group(2).strip().rstrip('.')
    else:
        driver_name = driver_block

    # strip leading competitor index like "[25] "
    driver_name = re.sub(r"^\s*\[\s*\d+\s*\]\s*", "", driver_name)

    lap_seconds = parse_time_value(lap_time)

    # skip clearly provisional / non-record announcements
    low = text.lower()
    if any(x in low for x in ("to be confirmed", "not a track record", "not a class record")):
        return None

    return {
        "classification": classification,
        "lap_time": lap_time,
        "lap_time_seconds": lap_seconds,
        "driver": driver_name,
        "marque": marque,
    }
