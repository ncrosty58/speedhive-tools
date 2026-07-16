"""Report top/bottom consistency ranking from the primary SQLite cache."""
from __future__ import annotations

import argparse
import difflib
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Any

from speedhive.utils.lap_analysis import (
    compute_laps_and_enriched_from_storage,
    normalize_name,
    format_seconds,
    session_year,
)

if TYPE_CHECKING:
    from speedhive.storage import SpeedhiveStorage


def default_db_path() -> Path:
    db_path = os.environ.get("SPEEDHIVE_DB_PATH")
    if db_path:
        return Path(db_path)
    data_dir = os.environ.get("SPEEDHIVE_DATA_DIR", "./data")
    return Path(data_dir) / "speedhive.db"





def load_session_types_from_storage(storage: "SpeedhiveStorage", org: int) -> Dict[str, Dict]:
    """Return mapping of session id -> raw session payload from SQLite."""
    return storage.load_session_payloads(org)


def is_race_session(session_raw: Dict) -> bool:
    """Heuristic race-session detector."""
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


def matches_session_type(session_raw: Dict, session_type: str) -> bool:
    if not isinstance(session_raw, dict):
        return False
    if session_type == "all":
        return True

    kind = session_raw.get("type") or session_raw.get("sessionType") or session_raw.get("raceType") or ""
    if not isinstance(kind, str):
        kind = ""
    kind = kind.lower()

    name = session_raw.get("name") or session_raw.get("sessionName") or ""
    if not isinstance(name, str):
        name = ""
    name = name.lower()

    class_val = ""
    for key in ("classification", "class", "classificationName", "className"):
        val = session_raw.get(key)
        if isinstance(val, str):
            class_val = val.lower()
            break

    if session_type == "qualifying":
        return "qual" in kind or "qual" in name or "qual" in class_val
    elif session_type == "practice":
        for term in ("practice", "warmup", "warm-up", "test", "practice"):
            if term in kind or term in name or term in class_val:
                return True
        return False
    else: # default is "race"
        return is_race_session(session_raw)


def _pool_weighted_stats(parts: List[Tuple[int, float, float]]) -> Dict[str, Any]:
    """Pool (lap_count, mean, stdev) tuples into one lap-count-weighted
    {lap_count, mean, stdev, cv}. Shared by every aggregation below that
    combines several sessions'/years'/aliases' worth of stats for the same
    driver into one summary.
    """
    total_laps = sum(n for n, _, _ in parts)
    pooled_mean = sum(n * m for n, m, _ in parts) / total_laps

    # Pool variance within sessions only (exclude between-session pace differences)
    numer = sum((n - 1) * (stdev_v ** 2) for n, _, stdev_v in parts)
    denom = sum(n - 1 for n, _, _ in parts)
    pooled_var = numer / denom if denom > 0 else 0.0
    pooled_stdev = math.sqrt(pooled_var) if pooled_var > 0 else 0.0

    # Calculate pooled CV as scale-invariant weighted average of session CVs
    cv_numer = 0.0
    cv_denom = 0.0
    for n, mean_v, stdev_v in parts:
        if mean_v > 0:
            cv_v = stdev_v / mean_v
            cv_numer += n * cv_v
            cv_denom += n
    pooled_cv = (cv_numer / cv_denom) if cv_denom > 0 else None

    return {
        "lap_count": total_laps,
        "mean": pooled_mean,
        "stdev": pooled_stdev,
        "cv": pooled_cv,
    }


def aggregate_by_name(enriched: Dict[str, Dict], session_map: Dict[str, Dict], session_types: List[str] = None) -> Dict[str, Dict]:
    """Pool per-driver-key statistics by driver display name."""
    if not session_types:
        session_types = ["race"]
    grouped: Dict[str, List[Tuple[int, float, float]]] = defaultdict(list)
    for _, value in enriched.items():
        name = value.get("name")
        if not name:
            continue

        session_keys = value.get("session_keys") or []
        include = False
        for session_key in session_keys:
            if not (isinstance(session_key, str) and session_key.startswith("session") and "_pos" in session_key):
                continue
            try:
                sid = session_key.split("_")[0].replace("session", "")
                session_raw = session_map.get(sid, {})
                if any(matches_session_type(session_raw, t) for t in session_types):
                    include = True
                    break
            except Exception:
                continue
        if not include:
            continue

        lap_count = int(value.get("lap_count") or 0)
        mean_v = float(value.get("mean") or 0.0)
        stdev_v = float(value.get("stdev") or 0.0)
        if lap_count <= 0:
            continue
        grouped[str(name)].append((lap_count, mean_v, stdev_v))

    aggregated: Dict[str, Dict] = {}
    for name, parts in grouped.items():
        if sum(n for n, _, _ in parts) <= 0:
            continue
        aggregated[name] = _pool_weighted_stats(parts)
    return aggregated


def aggregate_by_name_and_year(
    enriched: Dict[str, Dict],
    session_map: Dict[str, Dict],
    session_types: List[str] = None,
) -> Dict[str, Dict[int, Dict]]:
    """Pool per-driver-key statistics by driver display name AND year.

    Same session-type matching and lap-count-weighted pooling as
    aggregate_by_name, just bucketed by year too -- feeds
    get_most_improved_rankings, which needs to compare a driver's stats
    across specific years rather than all-time. Names here are raw
    (unclustered) -- get_most_improved_rankings re-keys this by an existing
    cluster_names() result before comparing years, so aliasing is handled
    consistently with the rest of the consistency rankings.

    Returns {name: {year: {lap_count, mean, stdev, cv}}}.
    """
    if not session_types:
        session_types = ["race"]
    grouped: Dict[Tuple[str, int], List[Tuple[int, float, float]]] = defaultdict(list)
    for _, value in enriched.items():
        name = value.get("name")
        if not name:
            continue

        session_keys = value.get("session_keys") or []
        year = None
        for session_key in session_keys:
            if not (isinstance(session_key, str) and session_key.startswith("session") and "_pos" in session_key):
                continue
            try:
                sid = session_key.split("_")[0].replace("session", "")
                session_raw = session_map.get(sid, {})
                if any(matches_session_type(session_raw, t) for t in session_types):
                    year = session_year(session_raw)
                    break
            except Exception:
                continue
        if year is None:
            continue

        lap_count = int(value.get("lap_count") or 0)
        mean_v = float(value.get("mean") or 0.0)
        stdev_v = float(value.get("stdev") or 0.0)
        if lap_count <= 0:
            continue
        grouped[(str(name), year)].append((lap_count, mean_v, stdev_v))

    by_name_year: Dict[str, Dict[int, Dict]] = defaultdict(dict)
    for (name, year), parts in grouped.items():
        if sum(n for n, _, _ in parts) <= 0:
            continue
        by_name_year[name][year] = _pool_weighted_stats(parts)
    return dict(by_name_year)


def cluster_name_groups(by_name: Dict[str, Dict], threshold: float = 0.85) -> Dict[str, List[str]]:
    """Group similar display names together by fuzzy similarity, without
    touching their stats -- returns {canonical_name: [alias names, incl.
    itself]}. Shared by cluster_names (which also repools stats) and
    anything else that needs this exact same identity-grouping decision
    applied to differently-shaped data (e.g. get_most_improved_rankings's
    year-bucketed stats).
    """
    items = sorted(by_name.items(), key=lambda pair: -pair[1].get("lap_count", 0))
    clusters: List[Dict] = []
    for name, _stats in items:
        normalized = normalize_name(name)
        best_cluster = None
        best_score = 0.0
        len_norm = len(normalized)
        for cluster in clusters:
            len_clust = len(cluster["norm"])
            # Quick length-based heuristic filter to skip expensive SequenceMatcher ratio
            max_ratio = (2.0 * min(len_norm, len_clust)) / (len_norm + len_clust) if (len_norm + len_clust) > 0 else 0.0
            if max_ratio < threshold or max_ratio <= best_score:
                continue
            score = difflib.SequenceMatcher(None, normalized, cluster["norm"]).ratio()
            if score > best_score:
                best_score = score
                best_cluster = cluster
        if best_cluster is not None and best_score >= threshold:
            best_cluster["members"].append(name)
        else:
            clusters.append({"rep": name, "norm": normalized, "members": [name]})

    return {cluster["rep"]: cluster["members"] for cluster in clusters}


def cluster_names(by_name: Dict[str, Dict], threshold: float = 0.85) -> Dict[str, Dict]:
    """Cluster similar display names and repool stats."""
    groups = cluster_name_groups(by_name, threshold=threshold)

    merged: Dict[str, Dict] = {}
    for rep, aliases in groups.items():
        parts = []
        for name in aliases:
            stats = by_name.get(name, {})
            n = int(stats.get("lap_count") or 0)
            mean_v = float(stats.get("mean") or 0.0)
            stdev_v = float(stats.get("stdev") or 0.0)
            if n > 0:
                parts.append((n, mean_v, stdev_v))
        if not parts:
            continue
        pooled = _pool_weighted_stats(parts)
        pooled["aliases"] = aliases
        merged[rep] = pooled
    return merged


def get_consistency_rankings(
    clustered: Dict[str, Dict],
    min_laps: int = 20,
    limit: int = 15,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
    """Process clustered stats to get top/least consistent drivers and overall stats.

    Returns (top_consistent, least_consistent, total_drivers, total_laps_analyzed)
    """
    rows = []
    for name, data in clustered.items():
        if data.get("lap_count", 0) >= min_laps and data.get("cv") is not None:
            mean_v = data["mean"]
            stdev_v = data["stdev"]
            cv_v = data["cv"]
            rows.append({
                "name": name,
                "lap_count": data["lap_count"],
                "mean": mean_v,
                "mean_display": format_seconds(mean_v),
                "stdev": stdev_v,
                "stdev_display": f"{stdev_v:.3f}s" if stdev_v else "N/A",
                "cv": cv_v,
                "cv_display": f"{cv_v * 100:.2f}%" if cv_v is not None else "N/A",
                "aliases": data.get("aliases", []),
            })

    rows.sort(key=lambda r: r["cv"])
    top_consistent = rows[:limit]
    least_consistent = sorted(rows, key=lambda r: r["cv"], reverse=True)[:limit]

    total_drivers = len(clustered)
    total_laps_analyzed = sum(d.get("lap_count", 0) for d in clustered.values())

    return top_consistent, least_consistent, total_drivers, total_laps_analyzed


def get_most_improved_rankings(
    enriched: Dict[str, Dict],
    session_map: Dict[str, Dict],
    session_types: List[str] = None,
    min_laps: int = 20,
    limit: int = 15,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Rank drivers by how much their consistency (CV) has changed between
    their earliest and most recent qualifying year (lap_count >= min_laps in
    each) -- anchored to each driver's own history, not a fixed calendar-year
    pair, so a driver racing since 2015 and one who joined in 2023 are each
    measured against their own start. CV, not raw mean lap time, is used
    because it's self-relative and stays meaningful even if a driver's
    class/track mix changed between the two years. Drivers with fewer than
    2 qualifying years are excluded -- nothing to compare them against.

    Returns (most_improved, most_declined), each a list of rows sorted by
    CV delta (first-year CV minus last-year CV; positive = improved),
    limited to `limit`.
    """
    by_name = aggregate_by_name(enriched, session_map, session_types=session_types)
    clusters = cluster_names(by_name)
    by_name_year_raw = aggregate_by_name_and_year(enriched, session_map, session_types=session_types)

    # Re-key the raw (unclustered) year-bucketed stats using the same
    # name-clustering decision already made above, so a driver whose name
    # was spelled differently in an early vs. a recent year still counts as
    # one person here.
    by_name_year: Dict[str, Dict[int, Dict]] = {}
    for canonical, data in clusters.items():
        years: Dict[int, List[Tuple[int, float, float]]] = defaultdict(list)
        for alias in data.get("aliases", [canonical]):
            for year, stats in by_name_year_raw.get(alias, {}).items():
                n = stats.get("lap_count", 0)
                if n > 0:
                    years[year].append((n, stats["mean"], stats["stdev"]))
        if years:
            by_name_year[canonical] = {year: _pool_weighted_stats(parts) for year, parts in years.items()}

    rows = []
    for name, years in by_name_year.items():
        qualifying_years = sorted(
            y for y, stats in years.items()
            if stats.get("lap_count", 0) >= min_laps and stats.get("cv") is not None
        )
        if len(qualifying_years) < 2:
            continue
        first_year, last_year = qualifying_years[0], qualifying_years[-1]
        first_cv = years[first_year]["cv"]
        last_cv = years[last_year]["cv"]
        delta = first_cv - last_cv
        rows.append({
            "name": name,
            "aliases": clusters.get(name, {}).get("aliases", [name]),
            "first_year": first_year,
            "last_year": last_year,
            "first_cv_display": f"{first_cv * 100:.2f}%",
            "last_cv_display": f"{last_cv * 100:.2f}%",
            "cv_delta": delta,
            "cv_delta_display": f"{delta * 100:+.2f}pp",
        })

    most_improved = sorted(rows, key=lambda r: r["cv_delta"], reverse=True)[:limit]
    most_declined = sorted(rows, key=lambda r: r["cv_delta"])[:limit]
    return most_improved, most_declined


def print_top_bottom(by_name: Dict[str, Dict], top_n: int = 10, min_laps: int = 20) -> None:
    """Print top and bottom CV rankings."""
    rows = [
        (name, data["lap_count"], data["mean"], data["stdev"], data["cv"])
        for name, data in by_name.items()
        if data.get("lap_count", 0) >= min_laps and data.get("cv") is not None
    ]
    if not rows:
        print("No drivers meet the min_laps / cv criteria")
        return
    rows_sorted = sorted(rows, key=lambda row: row[4])
    print(f"Top {top_n} most consistent drivers (lowest CV):")
    for name, laps, mean_v, stdev_v, cv in rows_sorted[:top_n]:
        print(f"- {name}: laps={laps}, mean={mean_v:.3f}, sd={stdev_v:.3f}, cv={cv:.3f}")
    print("")
    print(f"Bottom {top_n} least consistent drivers (highest CV):")
    for name, laps, mean_v, stdev_v, cv in rows_sorted[-top_n:][::-1]:
        print(f"- {name}: laps={laps}, mean={mean_v:.3f}, sd={stdev_v:.3f}, cv={cv:.3f}")


def find_driver_percentile(
    clustered: Dict[str, Dict],
    query: str,
    min_laps: int = 20,
    threshold: float = 0.85,
    nearby: int = 5,
) -> Optional[Dict]:
    """Find and print percentile rank of a target driver name."""
    rows = [
        (name, data["lap_count"], data.get("mean"), data.get("stdev"), data.get("cv"))
        for name, data in clustered.items()
        if data.get("lap_count", 0) >= min_laps and data.get("cv") is not None
    ]
    if not rows:
        print("No drivers meet the min_laps / cv criteria")
        return None

    rows_sorted = sorted(rows, key=lambda row: row[4])
    query_norm = normalize_name(query)
    best_name = None
    best_score = 0.0
    for rep_name, stats in clustered.items():
        score = difflib.SequenceMatcher(None, query_norm, normalize_name(rep_name)).ratio()
        if score > best_score:
            best_score = score
            best_name = rep_name
        for alias in stats.get("aliases", []):
            alias_score = difflib.SequenceMatcher(None, query_norm, normalize_name(alias)).ratio()
            if alias_score > best_score:
                best_score = alias_score
                best_name = rep_name

    if best_name is None or best_score < threshold:
        print(f"No fuzzy match for '{query}' above threshold {threshold} (best={best_score:.3f})")
        return None

    idx = next((i for i, row in enumerate(rows_sorted) if row[0] == best_name), None)
    if idx is None:
        print(f"Matched '{best_name}' was not present in the filtered set")
        return None

    total = len(rows_sorted)
    rank = idx + 1
    percentile = 100.0 * (total - rank) / total
    start = max(0, idx - nearby)
    end = min(total, idx + nearby + 1)
    nearby_rows = rows_sorted[start:end]

    print(f"Matched '{query}' -> '{best_name}' (score={best_score:.3f})")
    print(f"Rank: {rank}/{total}, percentile={percentile:.1f}%")
    print("")
    print(f"Nearby drivers (±{nearby}):")
    for i, (name, laps, mean_v, stdev_v, cv) in enumerate(nearby_rows, start=start + 1):
        marker = "*" if name == best_name else " "
        print(f"{i:4d}. {marker} {name}: laps={laps}, mean={mean_v:.3f}, sd={stdev_v:.3f}, cv={cv:.3f}")

    return {
        "matched": best_name,
        "score": best_score,
        "rank": rank,
        "total": total,
        "percentile": percentile,
        "nearby": nearby_rows,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Report top/bottom consistency from the primary SQLite cache")
    parser.add_argument("--org", type=int, required=True)
    parser.add_argument("--db-path", type=Path, default=default_db_path())
    parser.add_argument("--out-dir", type=Path, default=Path("output"))
    parser.add_argument("--min-laps", type=int, default=20)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--driver", "--name", dest="driver", type=str, default=None)
    parser.add_argument("--ignore-outliers", action="store_true", help="Ignore outlier lap times using IQR method")
    args = parser.parse_args(argv)

    if not args.db_path.exists():
        print(f"Error: Database file does not exist at '{args.db_path}'. Please sync or import first.", file=sys.stderr)
        return 1

    from speedhive.storage import SpeedhiveStorage
    storage = SpeedhiveStorage(args.db_path)
    if not storage.org_has_sessions(args.org):
        print(f"Error: Organization #{args.org} has no sessions in the database. Please sync or import first.", file=sys.stderr)
        return 1

    _, enriched = compute_laps_and_enriched_from_storage(storage, args.org, ignore_outliers=args.ignore_outliers)
    session_map = load_session_types_from_storage(storage, args.org)
    by_name = aggregate_by_name(enriched, session_map)
    clustered = cluster_names(by_name, threshold=args.threshold)
    print_top_bottom(clustered, top_n=args.top, min_laps=args.min_laps)
    if args.driver:
        print("\nDriver percentile query:\n")
        find_driver_percentile(
            clustered,
            args.driver,
            min_laps=args.min_laps,
            threshold=args.threshold,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
