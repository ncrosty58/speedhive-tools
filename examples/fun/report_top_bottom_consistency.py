#!/usr/bin/env python3
"""Report top/bottom most consistent drivers aggregated by name.

Reads:
- output/consistency_<org>_enriched.json
- output/full_dump/<org>/sessions.ndjson(.gz)

Logic:
- Filter to sessions that are races (heuristic: session raw has 'type' == 'race' or 'race' in name)
- For each `driver_key` entry in consistency enriched, collect its session_keys and driver stats
- Map session_keys to their session_id and check if that session_id is a race; ignore non-race entries
- Aggregate per driver name: combine lap counts and compute weighted mean/stdev? We'll aggregate by pooling laps via mean of CV weighted by lap_count to get overall CV; also compute overall lap_count and mean.

Output: print top 10 (lowest CV) and bottom 10 (highest CV) drivers with at least N laps (default 20)
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import statistics
import difflib
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def open_ndjson(path: Path):
    if not path.exists():
        return
    fh = gzip.open(path, "rt", encoding="utf8") if path.suffix == ".gz" or path.name.endswith('.gz') else open(path, "r", encoding="utf8")
    for ln in fh:
        ln = ln.strip()
        if not ln:
            continue
        try:
            yield json.loads(ln)
        except Exception:
            continue
    fh.close()


def load_enriched(out_dir: Path, org: int) -> Dict[str, Dict]:
    p = out_dir / f"consistency_{org}_enriched.json"
    with open(p, "r", encoding="utf8") as fh:
        return json.load(fh)


def load_session_types(dump_dir: Path, org: int) -> Dict[str, Dict]:
    """Return mapping session_id -> raw session object (to find classification/type).
    Use heuristics to detect race sessions.
    """
    dump = dump_dir / str(org)
    sess_path = dump / "sessions.ndjson.gz"
    if not sess_path.exists():
        sess_path = dump / "sessions.ndjson"
    mapping = {}
    if not sess_path.exists():
        return mapping
    for obj in open_ndjson(sess_path):
        sid = obj.get("session_id") or obj.get("sessionId") or (obj.get("raw") or {}).get("id")
        if sid is None:
            continue
        sid = str(int(sid))
        # raw session payload preferred
        raw = obj.get("raw") or obj
        mapping[sid] = raw
    return mapping


def is_race_session(session_raw: Dict) -> bool:
    # Heuristics: look for session_raw['type']=='race', or 'race' in name, or classification has 'race'
    if not isinstance(session_raw, dict):
        return False
    t = session_raw.get("type") or session_raw.get("sessionType") or session_raw.get("raceType")
    if isinstance(t, str) and t.lower() == "race":
        return True
    name = session_raw.get("name") or session_raw.get("sessionName") or ""
    if isinstance(name, str) and "race" in name.lower():
        return True
    # classification/grouping keys
    for k in ("classification", "class", "classificationName", "className"):
        v = session_raw.get(k)
        if isinstance(v, str) and "race" in v.lower():
            return True
    return False


def aggregate_by_name(enriched: Dict[str, Dict], session_map: Dict[str, Dict]) -> Dict[str, Dict]:
    """Aggregate stats per driver name across sessions, only include entries whose session_keys correspond to race sessions.

    Strategy:
    - For each enriched entry (driver_key), look at its session_keys. Extract session IDs and check is_race_session.
    - If any of the session_keys map to a race session, include this entry's stats.
    - Aggregate by name: collect lap_count and mean, stdev. We'll compute pooled variance by reconstructing an approximate pooled variance using mean/stdev and counts:
      pooled_mean = sum(mean_i * n_i) / N
      pooled_var = (sum((n_i-1)*sd_i^2 + n_i*(mean_i - pooled_mean)^2) ) / (N-1)
      pooled_stdev = sqrt(pooled_var)
      pooled_cv = pooled_stdev / pooled_mean
    """
    by_name: Dict[str, Dict] = {}
    temp: Dict[str, List[Tuple[int, float, float]]] = defaultdict(list)
    for key, v in enriched.items():
        name = v.get("name")
        if not name:
            continue
        sess_keys = v.get("session_keys") or []
        # determine if any session_key corresponds to a race
        included = False
        for sk in sess_keys:
            m = None
            # expected format session12345_pos6
            if sk.startswith("session") and "_pos" in sk:
                try:
                    sid = sk.split("_")[0].replace("session", "")
                    raw = session_map.get(sid)
                    if raw and is_race_session(raw):
                        included = True
                        break
                except Exception:
                    pass
        if not included:
            continue
        n = v.get("lap_count") or 0
        mean_v = v.get("mean") or 0.0
        sd_v = v.get("stdev") or 0.0
        if n <= 0:
            continue
        temp[name].append((n, mean_v, sd_v))

    # compute pooled stats
    for name, parts in temp.items():
        N = sum(n for n,_,_ in parts)
        if N <= 0:
            continue
        pooled_mean = sum(n * m for n, m, s in parts) / N
        # pooled variance numerator
        numer = 0.0
        for n, m, s in parts:
            # contribution: (n-1)*s^2 + n*(m - pooled_mean)^2
            numer += ((n - 1) * (s ** 2)) + (n * ((m - pooled_mean) ** 2))
        pooled_var = numer / (N - 1) if N > 1 else 0.0
        pooled_sd = math.sqrt(pooled_var) if pooled_var > 0 else 0.0
        pooled_cv = (pooled_sd / pooled_mean) if pooled_mean else None
        by_name[name] = {
            "lap_count": N,
            "mean": pooled_mean,
            "stdev": pooled_sd,
            "cv": pooled_cv,
        }
    return by_name


def normalize_name(name: str) -> str:
    s = (name or "").lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s.strip()


def cluster_names(by_name: Dict[str, Dict], threshold: float = 0.85) -> Dict[str, Dict]:
    """Cluster similar names using SequenceMatcher and merge pooled stats.

    Returns mapping representative_name -> pooled stats (lap_count, mean, stdev, cv, aliases)
    """
    # sort names by lap_count desc so large/likely canonical names become cluster reps
    items = sorted(by_name.items(), key=lambda kv: -kv[1].get("lap_count", 0))
    clusters: List[Dict] = []
    for name, stats in items:
        norm = normalize_name(name)
        best = None
        best_score = 0.0
        for c in clusters:
            score = difflib.SequenceMatcher(None, norm, c["norm"]).ratio()
            if score > best_score:
                best_score = score
                best = c
        if best is not None and best_score >= threshold:
            best["members"].append((name, stats))
        else:
            clusters.append({"rep": name, "norm": norm, "members": [(name, stats)]})

    merged: Dict[str, Dict] = {}
    for c in clusters:
        members = c["members"]
        # pool stats across members
        parts = []
        for name, s in members:
            n = s.get("lap_count") or 0
            mean_v = s.get("mean") or 0.0
            sd_v = s.get("stdev") or 0.0
            if n > 0:
                parts.append((n, mean_v, sd_v))
        if not parts:
            continue
        N = sum(n for n, _, _ in parts)
        pooled_mean = sum(n * m for n, m, _ in parts) / N
        numer = 0.0
        for n, m, s in parts:
            numer += ((n - 1) * (s ** 2)) + (n * ((m - pooled_mean) ** 2))
        pooled_var = numer / (N - 1) if N > 1 else 0.0
        pooled_sd = math.sqrt(pooled_var) if pooled_var > 0 else 0.0
        pooled_cv = (pooled_sd / pooled_mean) if pooled_mean else None
        merged[c["rep"]] = {
            "lap_count": N,
            "mean": pooled_mean,
            "stdev": pooled_sd,
            "cv": pooled_cv,
            "aliases": [n for n, _ in members],
        }
    return merged


def print_top_bottom(by_name: Dict[str, Dict], top_n: int = 10, min_laps: int = 20):
    # filter by min_laps and existing cv
    rows = [(name, d["lap_count"], d["mean"], d["stdev"], d["cv"]) for name, d in by_name.items() if d.get("lap_count",0) >= min_laps and d.get("cv") is not None]
    if not rows:
        print("No drivers meet the min_laps / cv criteria")
        return
    rows_sorted = sorted(rows, key=lambda r: (r[4] if r[4] is not None else float("inf")))  # sort by cv ascending
    print(f"Top {top_n} most consistent drivers (lowest CV):")
    for name, n, mean_v, sd_v, cv in rows_sorted[:top_n]:
        print(f"- {name}: laps={n}, mean={mean_v:.3f}, sd={sd_v:.3f}, cv={cv:.3f}")
    print("")
    print(f"Bottom {top_n} least consistent drivers (highest CV):")
    for name, n, mean_v, sd_v, cv in rows_sorted[-top_n:][::-1]:
        print(f"- {name}: laps={n}, mean={mean_v:.3f}, sd={sd_v:.3f}, cv={cv:.3f}")


def find_driver_percentile(clustered: Dict[str, Dict], query: str, min_laps: int = 20, threshold: float = 0.85, nearby: int = 5):
    """Find driver's percentile among clustered drivers and print nearby entries.

    Returns a dict with match info or None if not found.
    """
    # Build sortable list
    rows = [(name, d["lap_count"], d.get("mean"), d.get("stdev"), d.get("cv")) for name, d in clustered.items() if d.get("lap_count", 0) >= min_laps and d.get("cv") is not None]
    if not rows:
        print("No drivers meet the min_laps / cv criteria")
        return None
    rows_sorted = sorted(rows, key=lambda r: (r[4] if r[4] is not None else float("inf")))

    # find best match for query among cluster reps and aliases (aliases support)
    qn = normalize_name(query)
    best_name = None
    best_score = 0.0
    for rep, stats in clustered.items():
        rep_norm = normalize_name(rep)
        score = difflib.SequenceMatcher(None, qn, rep_norm).ratio()
        if score > best_score:
            best_score = score
            best_name = rep
        # check aliases
        for alias in stats.get("aliases", []):
            a_norm = normalize_name(alias)
            a_score = difflib.SequenceMatcher(None, qn, a_norm).ratio()
            if a_score > best_score:
                best_score = a_score
                best_name = rep

    if best_score < threshold:
        print(f"No fuzzy match for '{query}' above threshold {threshold} (best={best_score:.3f})")
        return None

    # find rank
    total = len(rows_sorted)
    idx = next((i for i, r in enumerate(rows_sorted) if r[0] == best_name), None)
    if idx is None:
        print(f"Matched name '{best_name}' not present in filtered set")
        return None
    rank = idx + 1
    percentile = 100.0 * (total - rank) / total

    # prepare nearby slice
    start = max(0, idx - nearby)
    end = min(total, idx + nearby + 1)
    nearby_list = rows_sorted[start:end]

    print(f"Matched '{query}' -> '{best_name}' (score={best_score:.3f})")
    print(f"Rank: {rank}/{total}, percentile={percentile:.1f}%")
    print("")
    print(f"Nearby drivers (±{nearby}):")
    for i, (n, laps, mean_v, sd_v, cv) in enumerate(nearby_list, start=start+1):
        marker = "*" if n == best_name else " "
        print(f"{i:4d}. {marker} {n}: laps={laps}, mean={mean_v:.3f}, sd={sd_v:.3f}, cv={cv:.3f}")

    return {
        "matched": best_name,
        "score": best_score,
        "rank": rank,
        "total": total,
        "percentile": percentile,
        "nearby": nearby_list,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--org", type=int, required=True)
    p.add_argument("--dump-dir", type=Path, default=Path("output/full_dump"))
    p.add_argument("--out-dir", type=Path, default=Path("output"))
    p.add_argument("--min-laps", type=int, default=20, help="Minimum total laps to consider a driver")
    p.add_argument("--top", type=int, default=10, help="How many top/bottom drivers to show")
    p.add_argument("--threshold", type=float, default=0.85, help="Name similarity threshold (0-1) for clustering")
    p.add_argument("--driver", "--name", dest="driver", type=str, default=None, help="Driver name to query for percentile")
    args = p.parse_args()

    enriched = load_enriched(args.out_dir, args.org)
    session_map = load_session_types(args.dump_dir, args.org)
    by_name = aggregate_by_name(enriched, session_map)
    clustered = cluster_names(by_name, threshold=args.threshold)
    print_top_bottom(clustered, top_n=args.top, min_laps=args.min_laps)
    if args.driver:
        print("\nDriver percentile query:\n")
        find_driver_percentile(clustered, args.driver, min_laps=args.min_laps, threshold=args.threshold)

if __name__ == "__main__":
    main()
