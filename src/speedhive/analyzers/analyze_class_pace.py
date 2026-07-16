"""Average lap time per car class, by year -- pace-progression analysis."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Optional

from speedhive.analyzers.analyze_consistency import matches_session_type
from speedhive.utils.lap_analysis import first_non_empty


def _build_pos_class_map(results_rows: List[Dict]) -> Dict[int, str]:
    """Map result position -> car class for one session's results.

    Car class lives per-competitor (a session/"race group" often mixes
    several classes running together), not on the session itself -- see
    the `resultClass` field on each row in storage.load_results_payloads().
    """
    mapping: Dict[int, str] = {}
    if not isinstance(results_rows, list):
        return mapping
    for row in results_rows:
        if not isinstance(row, dict):
            continue
        pos = row.get("position") or row.get("pos")
        cls = first_non_empty(
            row.get("resultClass"),
            row.get("class"),
            row.get("classification"),
            row.get("className"),
        )
        if pos is None or not cls:
            continue
        try:
            mapping[int(pos)] = cls
        except (TypeError, ValueError):
            continue
    return mapping


def _class_group_key(class_name: str) -> str:
    """Grouping key for a raw class label -- case/whitespace-insensitive.

    `resultClass` is free text with a long tail of one-off spelling/spacing
    variants (e.g. "FV" vs "1 FV" vs "1  FV"); this only folds together exact
    case/whitespace differences, not genuinely different tokens -- real
    alias resolution (typo-level) is the org's curated `class_alias_map.json`
    territory (see speedhive.workflows.track_records.curation), out of scope
    here.
    """
    return re.sub(r"\s+", " ", class_name.strip()).upper()


def _session_year(session_raw: Dict) -> Optional[int]:
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


def compute_avg_lap_by_class_year(
    enriched: Dict[str, Dict],
    session_map: Dict[str, Dict],
    results_map: Dict[str, List[Dict]],
    session_types: Optional[List[str]] = None,
    min_total_laps: int = 15,
    max_classes: int = 20,
) -> Dict:
    """Average filtered lap time per (car class, event year), pooled across
    every driver-session entry in `enriched` whose session matches one of
    `session_types` (default ["race"]).

    `results_map` (session_id -> result rows, e.g.
    storage.load_results_payloads()) supplies car class per position -- class
    is a per-competitor field (`resultClass`), not a session-level one, since
    one session/race group commonly mixes several classes running together.

    `resultClass` is free text with a long one-off tail (typos, stray
    entries) once pooled across 20 years of history -- `min_total_laps`
    drops classes with too little data to be a meaningful trend line, and
    `max_classes` caps the chart to the highest-volume classes (by total lap
    count) so the legend stays readable. Pass max_classes=None for no cap.

    Returns {"years": [int, ...], "classes": [str, ...],
    "series": {class_name: [avg_seconds_or_None, ...]},
    "counts": {class_name: [lap_count, ...]}} -- series/counts values are
    positionally aligned with "years"; None marks a class/year with no laps.
    Classes are ordered by total lap count, descending.
    """
    if not session_types:
        session_types = ["race"]

    pooled: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
    label_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pos_class_cache: Dict[str, Dict[int, str]] = {}

    for key, value in enriched.items():
        sess_match = re.match(r"session(\d+)_pos(\d+)", key)
        if not sess_match:
            continue
        sid, pos = sess_match.group(1), int(sess_match.group(2))
        session_raw = session_map.get(sid, {})
        if not any(matches_session_type(session_raw, t) for t in session_types):
            continue

        if sid not in pos_class_cache:
            pos_class_cache[sid] = _build_pos_class_map(results_map.get(sid))
        raw_class = pos_class_cache[sid].get(pos)
        year = _session_year(session_raw)
        if not raw_class or year is None:
            continue

        filtered_laps = value.get("filtered_laps") or []
        if not filtered_laps:
            continue

        group_key = _class_group_key(raw_class)
        pooled[group_key][year].extend(filtered_laps)
        label_counts[group_key][raw_class] += len(filtered_laps)

    # Use each group's most-common raw spelling as the display label.
    display_label = {
        group_key: max(labels.items(), key=lambda pair: pair[1])[0]
        for group_key, labels in label_counts.items()
    }

    total_laps = {
        group_key: sum(len(laps) for laps in by_year.values())
        for group_key, by_year in pooled.items()
    }
    group_keys = [k for k in pooled if total_laps[k] >= min_total_laps]
    group_keys.sort(key=lambda k: total_laps[k], reverse=True)
    if max_classes is not None:
        group_keys = group_keys[:max_classes]

    years = sorted({year for k in group_keys for year in pooled[k]})

    series: Dict[str, List[Optional[float]]] = {}
    counts: Dict[str, List[int]] = {}
    classes: List[str] = []
    for group_key in group_keys:
        cls = display_label[group_key]
        classes.append(cls)
        by_year = pooled[group_key]
        series[cls] = []
        counts[cls] = []
        for year in years:
            laps = by_year.get(year)
            if laps:
                series[cls].append(sum(laps) / len(laps))
                counts[cls].append(len(laps))
            else:
                series[cls].append(None)
                counts[cls].append(0)

    return {"years": years, "classes": classes, "series": series, "counts": counts}
