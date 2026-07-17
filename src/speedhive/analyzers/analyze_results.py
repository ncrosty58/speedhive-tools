"""Race results analysis -- wins and podiums by car-class finishing position."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from speedhive.analyzers.analyze_consistency import cluster_name_groups, matches_session_type
from speedhive.utils.lap_analysis import dedupe_session_ids, normalize_name


def compute_wins_and_podiums(
    results_payloads: Dict[str, List[Any]],
    session_map: Dict[str, Dict],
    session_types: Optional[List[str]] = None,
    laps_payloads: Optional[Dict[str, List[Any]]] = None,
) -> Dict[str, Dict]:
    """Per-driver-name (unclustered) start/win/podium counts from class
    finishing position, across every synced session matching session_types.

    A start counts unless status is "DNS" (never took the green flag). A
    win (positionInClass == 1) or podium (positionInClass <= 3) additionally
    requires status == "Normal" -- a DNF or DQ can't be a classified result
    even if the position field is still populated.

    Returns {name: {"wins":, "podiums":, "starts":, "lap_count":}} --
    lap_count is an alias for starts, present only so cluster_name_groups'
    existing "prefer the alias with more recorded activity as canonical"
    sort heuristic (which reads pair[1].get("lap_count", 0)) picks a
    sensible representative name without a second clustering implementation.
    """
    if not session_types:
        session_types = ["race"]

    keep_sids = dedupe_session_ids(results_payloads, laps_payloads)
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"wins": 0, "podiums": 0, "starts": 0})

    for sid, rows in results_payloads.items():
        if sid not in keep_sids or not isinstance(rows, list):
            continue
        session_raw = session_map.get(sid, {})
        if not any(matches_session_type(session_raw, t) for t in session_types):
            continue

        for row in rows:
            if not isinstance(row, dict):
                continue
            status = row.get("status")
            if status == "DNS":
                continue
            name = row.get("name") or (row.get("competitor") or {}).get("name")
            if not name:
                continue

            entry = counts[name]
            entry["starts"] += 1

            if status != "Normal":
                continue
            pos_in_class = row.get("positionInClass")
            try:
                pos_in_class = int(pos_in_class)
            except (TypeError, ValueError):
                continue
            if pos_in_class == 1:
                entry["wins"] += 1
            if pos_in_class <= 3:
                entry["podiums"] += 1

    return {name: {**c, "lap_count": c["starts"]} for name, c in counts.items()}


def get_wins_podiums_rankings(
    results_payloads: Dict[str, List[Any]],
    session_map: Dict[str, Dict],
    session_types: Optional[List[str]] = None,
    min_starts: int = 3,
    limit: int = 15,
    laps_payloads: Optional[Dict[str, List[Any]]] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """Cluster driver name variants, sum wins/podiums/starts across aliases,
    drop anyone under min_starts (a single lucky class win in a one-off
    entry shouldn't top the board), and return (most_wins, most_podiums),
    each sorted descending and limited to `limit`.
    """
    raw = compute_wins_and_podiums(results_payloads, session_map, session_types=session_types, laps_payloads=laps_payloads)
    groups = cluster_name_groups(raw, threshold=0.85)

    rows = []
    for canonical, aliases in groups.items():
        wins = sum(raw[a]["wins"] for a in aliases if a in raw)
        podiums = sum(raw[a]["podiums"] for a in aliases if a in raw)
        starts = sum(raw[a]["starts"] for a in aliases if a in raw)
        if starts < min_starts:
            continue
        rows.append({
            "name": canonical,
            "aliases": aliases,
            "wins": wins,
            "podiums": podiums,
            "starts": starts,
            "win_rate_display": f"{(wins / starts * 100):.1f}%",
            "podium_rate_display": f"{(podiums / starts * 100):.1f}%",
        })

    most_wins = sorted(rows, key=lambda r: (r["wins"], r["podiums"]), reverse=True)[:limit]
    most_podiums = sorted(rows, key=lambda r: (r["podiums"], r["wins"]), reverse=True)[:limit]
    return most_wins, most_podiums


def compute_driver_directory(
    results_payloads: Dict[str, List[Any]],
    session_map: Dict[str, Dict],
    session_types: Optional[List[str]] = None,
    laps_payloads: Optional[Dict[str, List[Any]]] = None,
) -> Dict[str, Any]:
    """Full-population per-driver starts/wins/podiums with precomputed ranks,
    keyed by normalize_name() -- every raw spelling of a name collapses into
    one row and the most frequent spelling is kept for display.

    Unlike get_wins_podiums_rankings there is no fuzzy clustering and no
    minimum-starts cutoff: this population must stay identical to the driver
    report's rank tiles ("P769 of 1,670 drivers"), which count every
    normalized name that ever took a start.

    Returns {"drivers": [row, ...], "total_drivers": N} sorted by starts
    descending, each row: {"key", "name", "starts", "wins", "podiums",
    "win_pct", "podium_pct", "starts_rank", "wins_rank", "podiums_rank"}.
    """
    if not session_types:
        session_types = ["race"]

    keep_sids = dedupe_session_ids(results_payloads, laps_payloads)
    stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"starts": 0, "wins": 0, "podiums": 0})
    spellings: Dict[str, Counter] = defaultdict(Counter)

    for sid, rows in results_payloads.items():
        if sid not in keep_sids or not isinstance(rows, list):
            continue
        session_raw = session_map.get(sid, {})
        if not any(matches_session_type(session_raw, t) for t in session_types):
            continue

        for row in rows:
            if not isinstance(row, dict):
                continue
            status = row.get("status")
            if status == "DNS":
                continue
            name = row.get("name") or (row.get("competitor") or {}).get("name")
            if not name:
                continue

            key = normalize_name(name)
            spellings[key][name] += 1
            entry = stats[key]
            entry["starts"] += 1

            if status != "Normal":
                continue
            try:
                pos_in_class = int(row.get("positionInClass"))
            except (TypeError, ValueError):
                continue
            if pos_in_class == 1:
                entry["wins"] += 1
            if pos_in_class <= 3:
                entry["podiums"] += 1

    drivers = []
    for key, entry in stats.items():
        starts = entry["starts"]
        # Most frequent spelling wins; ties broken by length then text so the
        # pick is deterministic across recalcs.
        display = max(spellings[key].items(), key=lambda kv: (kv[1], len(kv[0]), kv[0]))[0]
        drivers.append({
            "key": key,
            "name": display,
            "starts": starts,
            "wins": entry["wins"],
            "podiums": entry["podiums"],
            "win_pct": round(entry["wins"] / starts * 100, 1) if starts else 0.0,
            "podium_pct": round(entry["podiums"] / starts * 100, 1) if starts else 0.0,
        })

    # Position-based ranks with deterministic tie order (count desc, then key).
    for field, rank_field in (("starts", "starts_rank"), ("wins", "wins_rank"), ("podiums", "podiums_rank")):
        ordered = sorted(drivers, key=lambda r: (-r[field], r["key"]))
        for idx, row in enumerate(ordered):
            row[rank_field] = idx + 1

    drivers.sort(key=lambda r: (-r["starts"], r["key"]))
    return {"drivers": drivers, "total_drivers": len(drivers)}
