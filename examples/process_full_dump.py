#!/usr/bin/env python3
"""Process an `export_full_dump` output tree and produce driver-aggregated files.

Generates:
- `output/laps_by_driver_<org>.json` : mapping driver_key -> list of lap seconds
- `output/consistency_<org>_enriched.json` : aggregated stats with name and session_keys

This script is conservative and uses heuristics to associate lap rows to
session-position keys (e.g. `session12345_pos1`). It does not call the API.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, List, Optional
import csv
import statistics


_time_re = re.compile(r"(?:(\d+):)?(\d+)(?:\.(\d+))?")


def parse_time_value(v: Any) -> Optional[float]:
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
    m = _time_re.search(s)
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


def open_ndjson(path: Path):
    if not path.exists():
        return []
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


def load_sessions(sess_path: Path) -> Dict[str, Dict]:
    sessions: Dict[str, Dict] = {}
    for obj in open_ndjson(sess_path):
        # expecting keys like session_id and raw
        sid = obj.get("session_id") or obj.get("sessionId") or (obj.get("raw", {}) or {}).get("id")
        if sid is None:
            continue
        sid = str(int(sid))
        sessions[sid] = obj.get("raw") or obj
    return sessions


def build_pos_name_map(session_raw: Dict) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    if not isinstance(session_raw, dict):
        return mapping
    # common patterns in session raw: results -> positions/list
    # try several nested keys
    candidates = []
    if isinstance(session_raw.get("results"), list):
        candidates.extend(session_raw.get("results") or [])
    if isinstance(session_raw.get("positions"), list):
        candidates.extend(session_raw.get("positions") or [])
    # groups -> sessions -> results
    for k in ("groups", "classifications"):
        if isinstance(session_raw.get(k), list):
            for g in session_raw.get(k, []):
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


def assign_row_to_key(session_id: str, row: Dict[str, Any], pos_map: Dict[int, str]) -> str:
    # Prefer explicit position fields
    for fld in ("position", "pos", "result_position", "start_position"):
        if fld in row and row.get(fld) is not None:
            try:
                p = int(row.get(fld))
                return f"session{session_id}_pos{p}"
            except Exception:
                pass
    # Try competitor id
    for fld in ("competitorId", "competitor_id", "id", "competitorId"):
        if fld in row and row.get(fld) is not None:
            return str(row.get(fld))
    # Try name-based matching to pos_map
    name_fields = ("competitor", "participant", "driver", "name")
    candidate_name = None
    for nf in name_fields:
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
                return f"session{session_id}_pos{p}"
    # fallback
    return f"session{session_id}_unknown"


def process_org(dump_dir: Path, out_dir: Path, org_id: int) -> None:
    dump_dir = dump_dir / str(org_id)
    if not dump_dir.exists():
        raise SystemExit(f"Dump directory {dump_dir} not found")

    # try gz and plain
    sess_path = dump_dir / "sessions.ndjson.gz"
    if not sess_path.exists():
        sess_path = dump_dir / "sessions.ndjson"
    laps_path = dump_dir / "laps.ndjson.gz"
    if not laps_path.exists():
        laps_path = dump_dir / "laps.ndjson"

    sessions = load_sessions(sess_path)

    # Build per-session pos->name maps
    session_pos_map: Dict[str, Dict[int, str]] = {}
    for sid, raw in sessions.items():
        session_pos_map[sid] = build_pos_name_map(raw)

    # Also load any explicit results.ndjson produced by the exporter.
    # These entries are written as objects: {org_id, event_id, event_name, session_id, results: [...]}
    results_path = dump_dir / "results.ndjson.gz"
    if not results_path.exists():
        results_path = dump_dir / "results.ndjson"
    if results_path.exists():
        for obj in open_ndjson(results_path):
            sid = obj.get("session_id") or obj.get("sessionId")
            if sid is None:
                continue
            sid = str(int(sid))
            rows = obj.get("results") or obj.get("rows") or []
            if not isinstance(rows, list):
                continue
            # Build mapping from this results block
            mapping: Dict[int, str] = {}
            for r in rows:
                try:
                    pos = r.get("position") or r.get("pos")
                    name = r.get("name") or (r.get("competitor") or {}).get("name")
                    if pos is not None and name:
                        mapping[int(pos)] = name
                except Exception:
                    continue
            # Merge with existing map, prefer explicit results values
            existing = session_pos_map.get(sid, {})
            merged = {**existing, **mapping}
            session_pos_map[sid] = merged

    laps_by_driver: Dict[str, List[float]] = defaultdict(list)

    # Read laps.ndjson entries
    for entry in open_ndjson(laps_path):
        sid = entry.get("session_id") or (entry.get("sessionId") or (entry.get("session", None)))
        if sid is None:
            continue
        sid = str(int(sid))
        rows = entry.get("rows") or entry.get("rows_list") or entry.get("rows_count") and entry.get("rows") or []
        if not isinstance(rows, list):
            continue
        pos_map = session_pos_map.get(sid, {})
        for row in rows:
            # Many lap payloads are per-competitor objects with a `laps` list.
            # If so, iterate nested laps and use the parent row for driver mapping.
            if isinstance(row.get("laps"), list):
                parent = row
                for lap in row.get("laps", []):
                    t = None
                    # Prefer lapTime fields from nested lap objects
                    for tf in ("lapTime", "lap_time", "time", "lapSeconds", "seconds"):
                        if tf in lap:
                            t = parse_time_value(lap.get(tf))
                            if t is not None:
                                break
                    if t is None:
                        # ignore fields like timeOfDay (epoch) to avoid false positives
                        continue
                    key = assign_row_to_key(sid, parent, pos_map)
                    laps_by_driver[key].append(t)
                continue

            # Otherwise, row itself may be a flat lap record
            t = None
            for tf in ("lapTime", "lap_time", "time", "lapSeconds", "seconds"):
                if tf in row:
                    t = parse_time_value(row.get(tf))
                    if t is not None:
                        break
            if t is None:
                # no clear lap time field found; skip this row
                continue
            key = assign_row_to_key(sid, row, pos_map)
            laps_by_driver[key].append(t)

    # Write laps_by_driver
    out_dir.mkdir(parents=True, exist_ok=True)
    laps_out = out_dir / f"laps_by_driver_{org_id}.json"
    with open(laps_out, "w", encoding="utf8") as fh:
        json.dump(laps_by_driver, fh, indent=2)

    # Create enriched stats (so name mappings are available for CSV fallback)
    enriched: Dict[str, Dict] = {}
    for key, laps in laps_by_driver.items():
        if not isinstance(laps, list) or not laps:
            continue
        n = len(laps)
        m = mean(laps)
        med = median(laps)
        sd = stdev(laps) if n > 1 else 0.0
        cv = sd / m if m else None
        # name from session pos map if key matches
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

    # Helper to extract session start time strings from loaded sessions
    START_KEYS = ("startTime", "start_time", "start", "date", "startAt", "startDateTime", "eventDate", "event_date", "scheduledAt")
    def get_session_start(sid: str) -> Optional[str]:
        raw = sessions.get(sid)
        if not raw:
            return None
        # raw may be dict with nested keys
        for k in START_KEYS:
            v = raw.get(k)
            if isinstance(v, str) and v:
                return v
            if isinstance(v, (int, float)):
                try:
                    return datetime.utcfromtimestamp(float(v)).isoformat() + "Z"
                except Exception:
                    continue
        # sometimes nested under 'raw' again (defensive)
        nested = (raw.get("raw") or {}) if isinstance(raw, dict) else {}
        for k in START_KEYS:
            v = nested.get(k)
            if isinstance(v, str) and v:
                return v
            if isinstance(v, (int, float)):
                try:
                    return datetime.utcfromtimestamp(float(v)).isoformat() + "Z"
                except Exception:
                    continue
        return None

    # Create a CSV of lap rows with attached session start times.
    csv_out = out_dir / f"driver_laps_{org_id}_with_dates.csv"
    with open(csv_out, "w", encoding="utf8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["session_key", "session_id", "session_start", "driver_id", "driver_name", "lap_index", "lap_time_seconds"])
        for sk, laps in laps_by_driver.items():
            # parse session id from key if present
            m = re.match(r"session(\d+)_pos\d+", sk)
            sid = m.group(1) if m else None
            st = get_session_start(sid) if sid else None
            info = session_pos_map.get(sid, {}) if sid else {}
            name = None
            # try to find a name from the session_pos_map if possible
            if sid and isinstance(info, dict):
                # attempt to find position from key
                pm = re.match(r"session\d+_pos(\d+)", sk)
                try:
                    if pm:
                        pos = int(pm.group(1))
                        name = info.get(pos)
                except Exception:
                    name = None
            # fallback to enriched name mapping
            if not name:
                en = {} if not isinstance(enriched.get(sk), dict) else enriched.get(sk)
                name = en.get("name")
            if not name:
                name = sk
            if isinstance(laps, list):
                for i, lt in enumerate(laps, start=1):
                    try:
                        val = float(lt)
                    except Exception:
                        continue
                    writer.writerow([sk, sid or "", st or "", sk, name, i, val])

    # Build per-session summary CSV (aggregates of lap rows grouped by session_key)
    sess_agg: Dict[str, List[float]] = defaultdict(list)
    # read back the CSV we just wrote (avoids duplicating parsing logic)
    with open(csv_out, "r", encoding="utf8") as fh:
        rdr = csv.DictReader(fh)
        for r in rdr:
            try:
                lt = float(r.get("lap_time_seconds") or 0)
            except Exception:
                continue
            sk = r.get("session_key")
            sess_agg[sk].append(lt)

    sess_summary = []
    for sk, lts in sess_agg.items():
        n = len(lts)
        m = statistics.mean(lts) if n else 0.0
        med = statistics.median(lts) if n else 0.0
        sd = statistics.pstdev(lts) if n else 0.0
        slope = None
        if n >= 3:
            xs = list(range(1, n + 1))
            xm = statistics.mean(xs)
            ym = m
            num = sum((x - xm) * (y - ym) for x, y in zip(xs, lts))
            den = sum((x - xm) ** 2 for x in xs)
            slope = num / den if den != 0 else 0.0
        # derive session_id and start
        sid = None
        st = None
        mm = re.match(r"session(\d+)_", sk)
        if mm:
            sid = mm.group(1)
            st = get_session_start(sid)
        sess_summary.append({"session_key": sk, "session_id": sid, "session_start": st, "n": n, "mean": m, "median": med, "stdev": sd, "slope_per_lap": slope})

    ss_out = out_dir / f"session_summary_{org_id}.csv"
    with open(ss_out, "w", encoding="utf8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["session_key", "session_id", "session_start", "n", "mean", "median", "stdev", "slope_per_lap"])
        w.writeheader()
        for r in sorted(sess_summary, key=lambda x: (x.get("session_start") or "", x.get("session_key"))):
            w.writerow(r)

    # Short time-analysis summary: yearly medians and ICC
    year_stats: Dict[int, List[float]] = defaultdict(list)
    for r in sess_summary:
        st = r.get("session_start")
        if not st:
            continue
        try:
            dt = datetime.fromisoformat(st.replace("Z", ""))
        except Exception:
            try:
                dt = datetime.fromisoformat(st)
            except Exception:
                continue
        year_stats[dt.year].append(r.get("mean", 0.0))

    means = [r["mean"] for r in sess_summary if r["n"] > 0]
    between = statistics.pvariance(means) if len(means) > 1 else 0.0
    within_list = []
    for sk, lts in sess_agg.items():
        if len(lts) > 1:
            within_list.append(statistics.pvariance(lts))
    within = statistics.mean(within_list) if within_list else 0.0
    icc = between / (between + within) if (between + within) > 0 else None

    summary_txt = out_dir / f"driver_time_analysis_summary_{org_id}.txt"
    with open(summary_txt, "w", encoding="utf8") as fh:
        fh.write(f"Total lap rows: {sum(len(v) for v in laps_by_driver.values())}\\n")
        fh.write(f"Total sessions (keys): {len(sess_agg)}\\n")
        fh.write(f"Yearly sessions: { {y: len(v) for y, v in year_stats.items()} }\\n")
        if icc is not None:
            fh.write(f"ICC between={between:.4f} within={within:.4f} ICC={icc:.4f}\\n")
        else:
            fh.write("ICC not computable\\n")

    # (enriched will be enhanced and written after session summaries below)
    # Build a lightweight index for on-demand per-driver extraction.
    # The index maps driver_key -> metadata: lap_count, name, session_keys, first_session_start, last_session_start, median
    index: Dict[str, Dict] = {}
    for key, info in enriched.items():
        try:
            lap_count = int(info.get("lap_count") or 0)
        except Exception:
            lap_count = 0
        session_keys = info.get("session_keys") or []
        name = info.get("name")
        # determine first/last session start from session_keys if possible
        starts = []
        for sk in session_keys:
            mm = re.match(r"session(\d+)_", sk)
            if mm:
                sid = mm.group(1)
                st = get_session_start(sid)
                if st:
                    starts.append(st)
        starts_sorted = sorted(starts)
        first = starts_sorted[0] if starts_sorted else None
        last = starts_sorted[-1] if starts_sorted else None
        index[key] = {
            "driver_key": key,
            "name": name,
            "lap_count": lap_count,
            "median": info.get("median") or info.get("mean"),
            "session_keys": session_keys,
            "first_session_start": first,
            "last_session_start": last,
        }

    index_out = out_dir / f"laps_index_{org_id}.json"
    try:
        with open(index_out, "w", encoding="utf8") as fh:
            json.dump(index, fh, indent=2)
    except Exception:
        pass


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dump-dir", type=Path, default=Path("output/full_dump"))
    p.add_argument("--out-dir", type=Path, default=Path("output"))
    p.add_argument("--org", type=int, required=True)
    args = p.parse_args(argv)
    process_org(args.dump_dir, args.out_dir, args.org)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
