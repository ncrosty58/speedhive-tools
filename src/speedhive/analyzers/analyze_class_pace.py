"""Average lap time per car class, by year -- pace-progression analysis."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Optional

from speedhive.analyzers.analyze_consistency import matches_session_type
from speedhive.utils.lap_analysis import (
    first_non_empty,
    normalize_classification,
    normalize_name,
    session_year,
)


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
    case/whitespace differences, not genuinely different tokens. Real alias
    resolution (e.g. "Spec Miata" == "SM") is layered on top by
    _resolve_class_group_key, below.
    """
    return re.sub(r"\s+", " ", class_name.strip()).upper()


def _resolve_class_group_key(class_name: str, alias_map: Optional[Dict]) -> str:
    """Grouping key for a raw class label, folding it through the org's
    curated class_alias_map.json (the same file and resolution logic track-
    record curation uses -- see normalize_classification) so e.g. "Spec
    Miata" and "SM" group together consistently everywhere, not just in
    curated track records.

    Ambiguous tokens (the alias map's `always_review` list) are left
    grouped by their own folded spelling rather than merged with anything
    -- matches curation's stance that they need a human to disambiguate,
    not a silent guess.

    Falls back to plain whitespace/case folding when no alias_map is given.
    """
    folded = _class_group_key(class_name)
    if not alias_map:
        return folded
    status, resolved = normalize_classification(folded, alias_map)
    return resolved if status == "ok" and resolved else folded


def compute_avg_lap_by_class_year(
    enriched: Dict[str, Dict],
    session_map: Dict[str, Dict],
    results_map: Dict[str, List[Dict]],
    session_types: Optional[List[str]] = None,
    min_total_laps: int = 15,
    max_classes: int = 20,
    alias_map: Optional[Dict] = None,
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

    `alias_map` (the org's class_alias_map.json, e.g. via
    speedhive.stores.track_records) folds genuinely different-looking class
    labels that are the same class (e.g. "Spec Miata" == "SM") together, the
    same way track-record curation already does -- see
    _resolve_class_group_key. Omit for plain whitespace/case-only grouping.

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
        year = session_year(session_raw)
        if not raw_class or year is None:
            continue

        filtered_laps = value.get("filtered_laps") or []
        if not filtered_laps:
            continue

        group_key = _resolve_class_group_key(raw_class, alias_map)
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


def compute_participation_by_year(
    enriched: Dict[str, Dict],
    session_map: Dict[str, Dict],
    session_types: Optional[List[str]] = None,
) -> Dict:
    """Distinct-driver headcount by year, combined across every car class --
    "how many different people raced with us this year," not total laps or
    total entries. A driver racing in multiple classes/sessions the same
    year is counted once for that year.

    Unlike compute_avg_lap_by_class_year, this needs no per-competitor class
    lookup (results_map) since classes aren't broken out here.

    Returns {"years": [int, ...], "distinct_drivers": [int, ...]} -- values
    positionally aligned with "years".
    """
    if not session_types:
        session_types = ["race"]

    drivers_by_year: Dict[int, set] = defaultdict(set)

    for key, value in enriched.items():
        sess_match = re.match(r"session(\d+)_pos(\d+)", key)
        if not sess_match:
            continue
        sid = sess_match.group(1)
        session_raw = session_map.get(sid, {})
        if not any(matches_session_type(session_raw, t) for t in session_types):
            continue

        year = session_year(session_raw)
        name = value.get("name")
        if year is None or not name:
            continue

        # Normalized (not fuzzy-clustered) so trivial spelling/case variants
        # of the same person aren't double-counted -- same bar used for
        # curated/rejected identity matching elsewhere in this codebase.
        drivers_by_year[year].add(normalize_name(name))

    years = sorted(drivers_by_year.keys())
    return {
        "years": years,
        "distinct_drivers": [len(drivers_by_year[year]) for year in years],
    }


def compute_participation_by_class_year(
    enriched: Dict[str, Dict],
    session_map: Dict[str, Dict],
    results_map: Dict[str, List[Dict]],
    session_types: Optional[List[str]] = None,
    max_classes: int = 10,
    alias_map: Optional[Dict] = None,
) -> Dict:
    """Distinct-driver headcount per (car class, year) -- ranks classes by
    their average annual participation, and supplies each class's own
    year-by-year headcount for drill-down.

    A class's average only counts years it actually had participants; a year
    with zero is excluded from the average rather than counted as a 0 --
    otherwise a class that started recently or folded early would look
    weaker than one that merely ran every year in the dataset.

    `alias_map` (the org's class_alias_map.json) folds genuinely
    different-looking labels that are the same class (e.g. "Spec Miata" ==
    "SM") together -- see _resolve_class_group_key. Omit for plain
    whitespace/case-only grouping.

    Returns {"classes": [str, ...], "avg_participants": [float, ...],
    "years_by_class": {class_name: [int, ...]},
    "participants_by_class": {class_name: [int, ...]}} -- classes ordered
    by average annual participants, descending, capped to max_classes.
    years_by_class/participants_by_class are positionally aligned per class
    and only list years that class actually had participants in.
    """
    if not session_types:
        session_types = ["race"]

    drivers_by_class_year: Dict[str, Dict[int, set]] = defaultdict(lambda: defaultdict(set))
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
        year = session_year(session_raw)
        name = value.get("name")
        if not raw_class or year is None or not name:
            continue

        group_key = _resolve_class_group_key(raw_class, alias_map)
        drivers_by_class_year[group_key][year].add(normalize_name(name))
        label_counts[group_key][raw_class] += 1

    display_label = {
        group_key: max(labels.items(), key=lambda pair: pair[1])[0]
        for group_key, labels in label_counts.items()
    }

    avg_by_group = {
        group_key: sum(len(s) for s in by_year.values()) / len(by_year)
        for group_key, by_year in drivers_by_class_year.items()
        if by_year
    }

    group_keys = sorted(avg_by_group, key=lambda k: avg_by_group[k], reverse=True)
    if max_classes is not None:
        group_keys = group_keys[:max_classes]

    classes: List[str] = []
    avg_participants: List[float] = []
    years_by_class: Dict[str, List[int]] = {}
    participants_by_class: Dict[str, List[int]] = {}
    for group_key in group_keys:
        cls = display_label[group_key]
        classes.append(cls)
        avg_participants.append(round(avg_by_group[group_key], 1))
        by_year = drivers_by_class_year[group_key]
        sorted_years = sorted(by_year.keys())
        years_by_class[cls] = sorted_years
        participants_by_class[cls] = [len(by_year[y]) for y in sorted_years]

    return {
        "classes": classes,
        "avg_participants": avg_participants,
        "years_by_class": years_by_class,
        "participants_by_class": participants_by_class,
    }
