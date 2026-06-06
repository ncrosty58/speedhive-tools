"""Report top/bottom consistency ranking from offline dump artifacts."""
from __future__ import annotations

import argparse
import difflib
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from speedhive.processing.lap_analysis import compute_laps_and_enriched, normalize_name
from speedhive.processing.ndjson import open_ndjson


def load_session_types(dump_dir: Path, org: int) -> Dict[str, Dict]:
    """Return mapping of session id -> raw session payload."""
    dump = dump_dir / str(org)
    path = dump / "sessions.ndjson.gz"
    if not path.exists():
        path = dump / "sessions.ndjson"
    mapping: Dict[str, Dict] = {}
    if not path.exists():
        return mapping
    for obj in open_ndjson(path):
        sid = obj.get("session_id") or obj.get("sessionId") or (obj.get("raw") or {}).get("id")
        if sid is None:
            continue
        mapping[str(int(sid))] = obj.get("raw") or obj
    return mapping


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


def aggregate_by_name(enriched: Dict[str, Dict], session_map: Dict[str, Dict]) -> Dict[str, Dict]:
    """Pool per-driver-key statistics by driver display name."""
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
                if is_race_session(session_map.get(sid, {})):
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
        total_laps = sum(n for n, _, _ in parts)
        if total_laps <= 0:
            continue
        pooled_mean = sum(n * m for n, m, _ in parts) / total_laps
        numer = 0.0
        for n, mean_v, stdev_v in parts:
            numer += ((n - 1) * (stdev_v ** 2)) + (n * ((mean_v - pooled_mean) ** 2))
        pooled_var = numer / (total_laps - 1) if total_laps > 1 else 0.0
        pooled_stdev = math.sqrt(pooled_var) if pooled_var > 0 else 0.0
        pooled_cv = (pooled_stdev / pooled_mean) if pooled_mean else None
        aggregated[name] = {
            "lap_count": total_laps,
            "mean": pooled_mean,
            "stdev": pooled_stdev,
            "cv": pooled_cv,
        }
    return aggregated


def cluster_names(by_name: Dict[str, Dict], threshold: float = 0.85) -> Dict[str, Dict]:
    """Cluster similar display names and repool stats."""
    items = sorted(by_name.items(), key=lambda pair: -pair[1].get("lap_count", 0))
    clusters: List[Dict] = []
    for name, stats in items:
        normalized = normalize_name(name)
        best_cluster = None
        best_score = 0.0
        for cluster in clusters:
            score = difflib.SequenceMatcher(None, normalized, cluster["norm"]).ratio()
            if score > best_score:
                best_score = score
                best_cluster = cluster
        if best_cluster is not None and best_score >= threshold:
            best_cluster["members"].append((name, stats))
        else:
            clusters.append({"rep": name, "norm": normalized, "members": [(name, stats)]})

    merged: Dict[str, Dict] = {}
    for cluster in clusters:
        parts = []
        aliases = []
        for name, stats in cluster["members"]:
            aliases.append(name)
            n = int(stats.get("lap_count") or 0)
            mean_v = float(stats.get("mean") or 0.0)
            stdev_v = float(stats.get("stdev") or 0.0)
            if n > 0:
                parts.append((n, mean_v, stdev_v))
        if not parts:
            continue
        total_laps = sum(n for n, _, _ in parts)
        pooled_mean = sum(n * m for n, m, _ in parts) / total_laps
        numer = 0.0
        for n, mean_v, stdev_v in parts:
            numer += ((n - 1) * (stdev_v ** 2)) + (n * ((mean_v - pooled_mean) ** 2))
        pooled_var = numer / (total_laps - 1) if total_laps > 1 else 0.0
        pooled_stdev = math.sqrt(pooled_var) if pooled_var > 0 else 0.0
        pooled_cv = (pooled_stdev / pooled_mean) if pooled_mean else None
        merged[cluster["rep"]] = {
            "lap_count": total_laps,
            "mean": pooled_mean,
            "stdev": pooled_stdev,
            "cv": pooled_cv,
            "aliases": aliases,
        }
    return merged


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
    parser = argparse.ArgumentParser(description="Report top/bottom consistency from an offline export dump")
    parser.add_argument("--org", type=int, required=True)
    parser.add_argument("--dump-dir", type=Path, default=Path("output"))
    parser.add_argument("--out-dir", type=Path, default=Path("output"))
    parser.add_argument("--min-laps", type=int, default=20)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--driver", "--name", dest="driver", type=str, default=None)
    args = parser.parse_args(argv)

    _, enriched = compute_laps_and_enriched(args.dump_dir, args.org)
    session_map = load_session_types(args.dump_dir, args.org)
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
