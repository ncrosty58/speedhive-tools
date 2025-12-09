#!/usr/bin/env python3
"""Produce a compact driver consistency report from cached outputs.

Usage:
  python examples/fun/report_driver_consistency.py --name "Nathan Crosty"

This script reads files under `output/` (laps_by_driver, consistency/enriched/merged)
and computes aggregated stats for a named driver, then ranks by CV and shows neighbors.
"""
from __future__ import annotations
import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Dict, Any, List, Tuple, Optional
import difflib





def load_json(p: Path) -> Any:
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding='utf8'))


def mad(xs: List[float], med: float | None = None) -> float | None:
    if not xs:
        return None
    if med is None:
        med = median(xs)
    return median([abs(x - med) for x in xs])


def aggregate_by_name(laps_by_driver: Dict[str, List[float]], enriched: Dict[str, Dict]) -> Dict[str, Dict]:
    groups: Dict[str, List[float]] = {}
    for driver_id, laps in laps_by_driver.items():
        if not isinstance(laps, list):
            continue
        name = None
        info = enriched.get(driver_id) if enriched else None
        if isinstance(info, dict):
            name = info.get('name')
        if not name:
            name = driver_id
        groups.setdefault(name, []).extend(laps)

    stats_by_name: Dict[str, Dict] = {}
    for name, xs in groups.items():
        n = len(xs)
        if n == 0:
            continue
        m = mean(xs)
        med = median(xs)
        sd = stdev(xs) if n > 1 else 0.0
        cv = sd / m if m else None
        md = mad(xs, med)
        stats_by_name[name] = {
            'lap_count': n,
            'mean': m,
            'median': med,
            'stdev': sd,
            'cv': cv,
            'mad': md,
        }
    return stats_by_name


def load_ndjson(path: Path):
    if not path.exists():
        return
    fh = open(path, "r", encoding="utf8")
    for ln in fh:
        ln = ln.strip()
        if not ln:
            continue
        try:
            yield json.loads(ln)
        except Exception:
            continue
    fh.close()


def normalize_name(n: str) -> str:
    if not n:
        return ""
    s = n.lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s.strip()


def extract_iso_date(raw: Dict) -> Optional[str]:
    if not isinstance(raw, dict):
        return None
    # common keys
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


def session_classification(session_raw: Dict) -> Optional[str]:
    if not isinstance(session_raw, dict):
        return None
    for k in ("classification", "class", "classificationName", "className"):
        v = session_raw.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # fallback: try nested groups
    if isinstance(session_raw.get("groups"), list):
        for g in session_raw.get("groups"):
            if isinstance(g, dict) and g.get("name"):
                return g.get("name")
    return None


def linear_trend(xs: List[float], ys: List[float]) -> Dict[str, float]:
    # xs: timestamps (float), ys: means
    n = len(xs)
    if n < 2:
        return {"slope": 0.0, "intercept": 0.0, "r2": 0.0}
    xmean = sum(xs) / n
    ymean = sum(ys) / n
    num = sum((xi - xmean) * (yi - ymean) for xi, yi in zip(xs, ys))
    den = sum((xi - xmean) ** 2 for xi in xs)
    slope = num / den if den != 0 else 0.0
    intercept = ymean - slope * xmean
    # r2
    ss_tot = sum((yi - ymean) ** 2 for yi in ys)
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot != 0 else 0.0
    return {"slope": slope, "intercept": intercept, "r2": r2}


def season_label(iso: Optional[str]) -> Optional[str]:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        m = dt.month
        if m in (3, 4, 5):
            return "spring"
        if m in (9, 10, 11):
            return "fall"
        return "other"
    except Exception:
        return None


def fuzzy_match_driver_keys(enriched: Dict[str, Dict], query: str, threshold: float = 0.85) -> List[str]:
    qn = normalize_name(query)
    # build set of distinct names
    names = {v.get('name') for v in enriched.values() if isinstance(v, dict) and v.get('name')}
    best = None
    best_score = 0.0
    for n in names:
        if not n:
            continue
        sc = difflib.SequenceMatcher(None, qn, normalize_name(n)).ratio()
        if sc > best_score:
            best_score = sc
            best = n
    matched_keys = []
    if best_score >= threshold and best:
        bn = normalize_name(best)
        for k, v in enriched.items():
            nm = (v.get('name') if isinstance(v, dict) else None)
            if not nm:
                continue
            if difflib.SequenceMatcher(None, normalize_name(nm), bn).ratio() >= threshold:
                matched_keys.append(k)
    else:
        for k, v in enriched.items():
            nm = (v.get('name') if isinstance(v, dict) else None)
            if not nm:
                continue
            if difflib.SequenceMatcher(None, qn, normalize_name(nm)).ratio() >= threshold:
                matched_keys.append(k)
    return matched_keys



def ranked_list(stats_by_name: Dict[str, Dict], min_laps: int) -> List[Tuple[str, float, int]]:
    rows = []
    for name, s in stats_by_name.items():
        cv = s.get('cv')
        lc = s.get('lap_count', 0)
        if cv is None or lc < min_laps:
            continue
        rows.append((name, float(cv), int(lc)))
    # sort by cv asc, prefer larger lap counts when equal
    rows.sort(key=lambda r: (r[1], -r[2]))
    return rows


def format_val(v) -> str:
    if v is None:
        return 'None'
    if isinstance(v, float):
        return f'{v:.6g}'
    return str(v)


def main() -> None:
    p = argparse.ArgumentParser(description='Driver consistency report from cached outputs')
    p.add_argument('--name', required=True, help='Driver name to report (case-insensitive substring match)')
    p.add_argument('--org', default='30476', help='Organization id (used for choosing output files)')
    p.add_argument('--min-laps-list', default='1,5,20,50', help='Comma separated min laps to report ranks for')
    p.add_argument('--threshold', type=float, default=0.80, help='Fuzzy match threshold (lower = more permissive). Matches `report_top_bottom_consistency.py` semantics')
    p.add_argument('--neighbors', type=int, default=5, help='How many neighbors to show around target')
    args = p.parse_args()

    out_dir = Path('output')
    laps_file = out_dir / f'laps_by_driver_{args.org}.json'
    enriched_file = out_dir / f'consistency_{args.org}_enriched.json'

    laps = load_json(laps_file) or {}
    enriched = load_json(enriched_file) or {}

    stats_by_name = aggregate_by_name(laps, enriched)

    # Reconstruct groups (name -> list of lap times) so we can pool across
    # multiple aggregated names if needed.
    groups: Dict[str, List[float]] = {}
    for driver_id, laps_list in (laps or {}).items():
        if not isinstance(laps_list, list):
            continue
        info = enriched.get(driver_id) if enriched else None
        name = None
        if isinstance(info, dict):
            name = info.get('name')
        if not name:
            name = driver_id
        groups.setdefault(name, []).extend([float(x) for x in laps_list])

    # find canonical key that matches provided name (case-insensitive substring)
    target = None
    lowered = args.name.lower()
    for name in stats_by_name.keys():
        if lowered in name.lower():
            target = name
            break

    if not target:
        # Try fuzzy matching against aggregated names (useful for alternate spellings)
        qn = normalize_name(args.name)
        best = None
        best_score = 0.0
        for name in stats_by_name.keys():
            sc = difflib.SequenceMatcher(None, qn, normalize_name(name)).ratio()
            if sc > best_score:
                best_score = sc
                best = name
        if best_score >= args.threshold and best:
            print(f'No exact substring match — using fuzzy match on aggregated names: matched "{best}" (score {best_score:.3f})')
            target = best
        else:
            print(f'No aggregated driver matching "{args.name}" found.')
            return

    # Find other aggregated names that are similar to the target (by threshold).
    ns = stats_by_name[target]
    qn = normalize_name(target)
    similar_names = [name for name in stats_by_name.keys() if difflib.SequenceMatcher(None, qn, normalize_name(name)).ratio() >= args.threshold]
    merged_names = []
    if len(similar_names) > 1:
        # pool laps across these aggregated names
        pooled = []
        for nm in similar_names:
            pooled.extend(groups.get(nm, []))
        if pooled:
            merged_names = similar_names
            n = len(pooled)
            m = mean(pooled)
            med = median(pooled)
            sd = stdev(pooled) if n > 1 else 0.0
            cv = sd / m if m else None
            md = mad(pooled, med)
            ns = {
                'lap_count': n,
                'mean': m,
                'median': med,
                'stdev': sd,
                'cv': cv,
                'mad': md,
            }
    print('Aggregated stats:')
    print(' name:', target)
    print(' lap_count:', ns['lap_count'])
    print(' mean:', format_val(ns['mean']))
    print(' median:', format_val(ns['median']))
    print(' stdev:', format_val(ns['stdev']))
    print(' cv:', format_val(ns['cv']))
    print(' mad:', format_val(ns['mad']))

    # Build an effective stats_by_name that reflects pooling when merged_names used.
    stats_by_name_effective = dict(stats_by_name)
    if merged_names:
        # Remove individual merged entries and replace with a single pooled target entry
        for nm in merged_names:
            if nm in stats_by_name_effective and nm != target:
                del stats_by_name_effective[nm]
        # set/replace target entry to pooled ns
        stats_by_name_effective[target] = ns

    min_laps_list = [int(x) for x in args.min_laps_list.split(',') if x.strip()]
    for ml in min_laps_list:
        rows = ranked_list(stats_by_name_effective, ml)
        total = len(rows)
        pos = None
        for i, (n, cv, lc) in enumerate(rows, start=1):
            if n == target:
                pos = i
                break
        pct = None
        if pos is not None and total > 0:
            # percentile: fraction of drivers this target is more consistent than
            pct = 100.0 * (total - pos) / total
        pct_str = f"{pct:.1f}%" if pct is not None else 'N/A'
        print(f'With min_laps={ml}: total names={total}, {target} position={pos}, percentile={pct_str}')

    # show neighbors for one of the common cutoffs (min_laps=5)
    rows5 = ranked_list(stats_by_name_effective, 5)
    total5 = len(rows5)
    pos5 = next((i for i,(n,cv,lc) in enumerate(rows5, start=1) if n==target), None)
    if pos5:
        idx = pos5 - 1
        start = max(0, idx - args.neighbors)
        end = min(total5, idx + args.neighbors + 1)
        print('\nNearby (min_laps=5) around %s:' % target)
        for i in range(start, end):
            n, cv, lc = rows5[i]
            marker = '*' if n == target else ' '
            print(f"{marker} {i+1:4d}. {n}  cv={cv:.4f}  laps={lc}")

    # (sample session keys print moved to after matched_keys is resolved)

    # --- Per-class breakdown and trends ---
    # Determine which session-level keys to use for per-class aggregation.
    # If we merged multiple aggregated names (merged_names is non-empty), prefer
    # to use all session aliases that belong to any of the merged aggregated names.
    if merged_names:
        matched_keys = [k for k, v in enriched.items() if isinstance(v, dict) and v.get('name') in merged_names]
        used_fuzzy = False
        if not matched_keys:
            # fallback: fuzzy match across enrichment map
            matched_keys = fuzzy_match_driver_keys(enriched, target, threshold=args.threshold)
            used_fuzzy = True
    else:
        # Prefer explicit session-level keys that were assigned the aggregated name
        matched_keys = [k for k, v in enriched.items() if isinstance(v, dict) and v.get('name') and target == v.get('name')]
        used_fuzzy = False
        if not matched_keys:
            matched_keys = fuzzy_match_driver_keys(enriched, target, threshold=args.threshold)
            used_fuzzy = True
    if not matched_keys:
        print('\nNo individual driver keys found for detailed per-class report.')
        return
    # now we have matched_keys; set session_keys and print a sample
    session_keys = matched_keys
    if session_keys:
        print('\nSession keys included (sample):', session_keys[:20])

    # load sessions map to read classification and dates
    dump_dir = Path('output/full_dump') / args.org
    sess_path = dump_dir / 'sessions.ndjson'
    if not sess_path.exists():
        sess_path = dump_dir / 'sessions.ndjson.gz'
    session_map = {}
    if sess_path.exists():
        for obj in load_ndjson(sess_path):
            sid = obj.get('session_id') or obj.get('sessionId') or (obj.get('raw') or {}).get('id')
            if sid is None:
                continue
            session_map[str(int(sid))] = obj.get('raw') or obj

    # group laps by classification
    laps_map = laps  # driver_key -> list of lap floats
    class_buckets = defaultdict(list)  # class -> list of lap values
    class_session_means = defaultdict(list)  # class -> list of (session_ts, mean)
    class_session_counts = defaultdict(int)
    overall_session_points: List[Tuple[float, float, str, Optional[str]]] = []  # (ts, mean, session_id, session_name)
    for dk in matched_keys:
        # get lap list
        laps_list = laps_map.get(dk) or []
        if not laps_list:
            continue
        # find session id from dk
        m = re.match(r'session(\d+)_pos', dk)
        sid = m.group(1) if m else None
        sess_raw = session_map.get(sid) if sid else None
        cls = session_classification(sess_raw) or 'unknown'
        # aggregate
        vals = [float(x) for x in laps_list]
        class_buckets[cls].extend(vals)
        class_session_counts[cls] += len(vals)
        # session mean for trend
        if vals:
            sess_date_iso = extract_iso_date(sess_raw) if sess_raw else None
            try:
                sess_ts = datetime.fromisoformat(sess_date_iso.replace('Z', '+00:00')).timestamp() if sess_date_iso else None
            except Exception:
                sess_ts = None
            if sess_ts is not None:
                class_session_means[cls].append((sess_ts, mean(vals)))
                # record for overall trend
                sess_name = (sess_raw.get('name') or sess_raw.get('sessionName')) if sess_raw else None
                overall_session_points.append((sess_ts, mean(vals), str(sid) if sid else '', sess_name))

    # compute per-class stats
    class_reports = {}
    for cls, vals in class_buckets.items():
        if not vals:
            continue
        n = len(vals)
        m = mean(vals)
        med = median(vals)
        sd = stdev(vals) if n > 1 else 0.0
        cv = sd / m if m else None
        md = mad(vals, med)
        # trends
        sess_points = sorted(class_session_means.get(cls, []), key=lambda x: x[0])
        if len(sess_points) >= 2:
            xs = [p[0] for p in sess_points]
            ys = [p[1] for p in sess_points]
            trend = linear_trend(xs, ys)
            # slope is seconds per second of timestamp; convert to seconds per day
            slope_per_day = trend['slope'] * 86400.0
        else:
            trend = {'slope': 0.0, 'intercept': 0.0, 'r2': 0.0}
            slope_per_day = 0.0
        # seasonal comparison
        seasons = defaultdict(list)
        for sid_ts, smean in class_session_means.get(cls, []):
            iso = datetime.utcfromtimestamp(sid_ts).isoformat()
            lab = season_label(iso)
            if lab:
                seasons[lab].append(smean)
        spring_mean = mean(seasons['spring']) if seasons.get('spring') else None
        fall_mean = mean(seasons['fall']) if seasons.get('fall') else None

        class_reports[cls] = {
            'lap_count': n,
            'mean': m,
            'median': med,
            'stdev': sd,
            'cv': cv,
            'mad': md,
            'trend': {
                'slope_per_day': slope_per_day,
                'r2': trend.get('r2'),
            },
            'seasonal': {
                'spring_mean': spring_mean,
                'fall_mean': fall_mean,
            },
        }

    # print report
    print('\nPer-class breakdown:')
    for cls, rep in sorted(class_reports.items(), key=lambda kv: -kv[1]['lap_count']):
        print(f"\nClass: {cls}")
        print(f"  laps: {rep['lap_count']}")
        print(f"  mean: {rep['mean']:.3f} median: {rep['median']:.3f} stdev: {rep['stdev']:.3f} cv: {rep['cv']:.3f}")
        slope = rep['trend']['slope_per_day']
        direction = 'no trend'
        if abs(slope) > 0.001:
            direction = 'faster' if slope < 0 else 'slower'
        print(f"  trend: {direction} (slope {slope:.4f} sec/day, r2={rep['trend']['r2']:.3f})")
        s_spring = rep['seasonal']['spring_mean']
        s_fall = rep['seasonal']['fall_mean']
        if s_spring is not None and s_fall is not None:
            diff = s_fall - s_spring
            which = 'faster in spring' if diff > 0 else 'faster in fall' if diff < 0 else 'no difference'
            print(f"  seasonal: spring_mean={s_spring:.3f}, fall_mean={s_fall:.3f} -> {which} (fall-spring={diff:.3f})")

    # matched aggregated names info (if merged_names present)
    matched_names_info = []
    if merged_names:
        for nm in merged_names:
            matched_names_info.append({'name': nm, 'lap_count': len(groups.get(nm, []))})
    else:
        # include the single target name
        matched_names_info = [{'name': target, 'lap_count': len(groups.get(target, []))}]

    # overall session-level trend (from session means)
    overall_trend = None
    if overall_session_points:
        pts = sorted(overall_session_points, key=lambda p: p[0])
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        tr = linear_trend(xs, ys)
        slope_per_day = tr['slope'] * 86400.0
        first_mean = ys[0]
        last_mean = ys[-1]
        change = last_mean - first_mean
        pct_change = (change / first_mean * 100.0) if first_mean else None
        first_iso = datetime.utcfromtimestamp(xs[0]).isoformat() + 'Z'
        last_iso = datetime.utcfromtimestamp(xs[-1]).isoformat() + 'Z'
        overall_trend = {
            'sessions': len(pts),
            'first_session_iso': first_iso,
            'last_session_iso': last_iso,
            'first_mean': first_mean,
            'last_mean': last_mean,
            'change_seconds': change,
            'pct_change': pct_change,
            'slope_per_day': slope_per_day,
            'r2': tr.get('r2'),
        }

    outp = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'driver_query': args.name,
        'target': target,
        'overall': ns,
        'per_class': class_reports,
        'session_keys_used': matched_keys,
        'used_fuzzy_match_for_keys': used_fuzzy,
        'matched_aggregated_names': matched_names_info,
        'overall_session_trend': overall_trend,
    }
    fname = out_dir / f'driver_report_{args.org}_{re.sub(r"[^A-Za-z0-9_-]","_", target)[:120]}.json'
    txtpath = fname.with_suffix('.txt')
    # ensure output dir exists and remove old files so we always write fresh
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        if fname.exists():
            fname.unlink()
    except Exception:
        pass
    try:
        if txtpath.exists():
            txtpath.unlink()
    except Exception:
        pass
    with open(fname, 'w', encoding='utf8') as fh:
        json.dump(outp, fh, indent=2)
    print(f"\nWrote report to {fname}")
    # Also produce a human-readable English narrative summary
    txt_lines: List[str] = []
    txt_lines.append(f"Driver consistency report for {target} (org {args.org})")
    txt_lines.append(f"Generated: {outp['generated_at']}")
    txt_lines.append("")
    overall = outp['overall']
    txt_lines.append(f"Overall summary:")
    txt_lines.append(f"- Total laps considered: {overall.get('lap_count', 0)}")
    txt_lines.append(f"- Mean lap time: {overall.get('mean'):.3f} s")
    txt_lines.append(f"- Median lap time: {overall.get('median'):.3f} s")
    txt_lines.append(f"- Standard deviation: {overall.get('stdev'):.3f} s")
    txt_lines.append(f"- Coefficient of variation (CV): {overall.get('cv'):.3f}")
    txt_lines.append(f"- Median absolute deviation (MAD): {overall.get('mad'):.3f} s")
    txt_lines.append("")
    txt_lines.append("Ranking context:")
    for ml in min_laps_list:
        rows = ranked_list(stats_by_name_effective, ml)
        total = len(rows)
        pos = None
        for i, (n, cv, lc) in enumerate(rows, start=1):
            if n == target:
                pos = i
                break
        if pos is None:
            txt_lines.append(f"- With minimum {ml} laps: {target} is not ranked (insufficient laps)")
        else:
            pct = 100.0 * (total - pos) / total if total > 0 else 0.0
            txt_lines.append(f"- With minimum {ml} laps: ranked {pos}/{total} (more consistent than {pct:.1f}% of drivers in this cohort)")
    txt_lines.append("")
    txt_lines.append("Per-class details:")
    if not class_reports:
        txt_lines.append("No per-class data available for this driver.")
    for cls, rep in sorted(class_reports.items(), key=lambda kv: -kv[1]['lap_count']):
        txt_lines.append("")
        txt_lines.append(f"Class: {cls}")
        txt_lines.append(f"- Laps: {rep['lap_count']}")
        txt_lines.append(f"- Mean lap: {rep['mean']:.3f} s, median: {rep['median']:.3f} s")
        txt_lines.append(f"- Std dev: {rep['stdev']:.3f} s, CV: {rep['cv']:.3f}, MAD: {rep['mad']:.3f} s")
        slope = rep['trend']['slope_per_day']
        if abs(slope) < 0.001:
            txt_lines.append(f"- Trend: no meaningful change in speed over time (slope ≈ {slope:.4f} s/day)")
        else:
            direction = 'faster' if slope < 0 else 'slower'
            txt_lines.append(f"- Trend: on average the driver is getting {direction} by about {abs(slope):.3f} seconds per day (r²={rep['trend']['r2']:.3f})")
        s_spring = rep['seasonal'].get('spring_mean')
        s_fall = rep['seasonal'].get('fall_mean')
        if s_spring is None and s_fall is None:
            txt_lines.append(f"- Seasonal: insufficient data for spring vs fall comparison")
        else:
            if s_spring is None:
                txt_lines.append(f"- Seasonal: no spring sessions to compare; fall mean = {s_fall:.3f} s")
            elif s_fall is None:
                txt_lines.append(f"- Seasonal: no fall sessions to compare; spring mean = {s_spring:.3f} s")
            else:
                diff = s_fall - s_spring
                if abs(diff) < 0.001:
                    txt_lines.append(f"- Seasonal: no meaningful difference between spring ({s_spring:.3f}s) and fall ({s_fall:.3f}s)")
                elif diff > 0:
                    txt_lines.append(f"- Seasonal: the driver is on average {diff:.3f} s faster in spring than in fall (spring mean {s_spring:.3f}s vs fall mean {s_fall:.3f}s)")
                else:
                    txt_lines.append(f"- Seasonal: the driver is on average {abs(diff):.3f} s faster in fall than in spring (fall mean {s_fall:.3f}s vs spring mean {s_spring:.3f}s)")

    txt_lines.append("")
    # provenance: which aggregated names were included (and their lap counts)
    txt_lines.append("Matched aggregated names:")
    for ni in matched_names_info:
        txt_lines.append(f"- {ni['name']}: {ni['lap_count']} laps")
    if used_fuzzy:
        txt_lines.append(f"- Note: session keys were selected by fuzzy matching with threshold={args.threshold}")

    # overall session trend narrative (if available)
    if overall_trend:
        txt_lines.append("")
        txt_lines.append("Trend over sessions:")
        txt_lines.append(f"- Sessions used for trend: {overall_trend['sessions']}")
        txt_lines.append(f"- Date range: {overall_trend['first_session_iso']} to {overall_trend['last_session_iso']}")
        txt_lines.append(f"- First session mean lap: {overall_trend['first_mean']:.3f} s")
        txt_lines.append(f"- Last session mean lap: {overall_trend['last_mean']:.3f} s")
        ch = overall_trend['change_seconds']
        pct = overall_trend['pct_change']
        direction = 'faster' if ch < 0 else 'slower' if ch > 0 else 'no net change'
        if pct is not None:
            txt_lines.append(f"- Overall change: {abs(ch):.3f} s ({abs(pct):.2f}%) — on balance the driver is {direction} at the end compared to the start")
        else:
            txt_lines.append(f"- Overall change: {abs(ch):.3f} s — on balance the driver is {direction} at the end compared to the start")
        txt_lines.append(f"- Trend slope: {overall_trend['slope_per_day']:.4f} s/day (r²={overall_trend['r2']:.3f})")
        # qualitative summary
        if abs(overall_trend['slope_per_day']) > 0.5:
            txt_lines.append("- Qualitative: notable change over time — consider inspecting per-session means for non-linear patterns or outliers.")
        elif abs(overall_trend['slope_per_day']) > 0.05:
            txt_lines.append("- Qualitative: modest trend over time; likely gradual improvement or decline.")
        else:
            txt_lines.append("- Qualitative: no strong linear trend across sessions; variance may be driven by session-to-session conditions or outliers.")
        # richer narrative paragraph describing the trend over years
        try:
            slope_per_year = overall_trend['slope_per_day'] * 365.25
            abs_change = abs(overall_trend['change_seconds'])
            pct = overall_trend['pct_change']
            first_iso = overall_trend['first_session_iso']
            last_iso = overall_trend['last_session_iso']
            sessions_n = overall_trend['sessions']
            if pct is None:
                pct_str = 'an absolute change of {0:.3f} seconds'.format(abs_change)
            else:
                pct_str = '{0:.3f} seconds ({1:.2f}%)'.format(abs_change, abs(pct))
            trend_dir = 'faster' if overall_trend['change_seconds'] < 0 else 'slower' if overall_trend['change_seconds'] > 0 else 'no net change'
            txt_lines.append("")
            txt_lines.append("Narrative summary of performance over time:")
            txt_lines.append(f"- Across {sessions_n} session means between {first_iso} and {last_iso}, the driver's pooled mean lap changed by {pct_str}, i.e. the driver is {trend_dir} at the end of the period.")
            txt_lines.append(f"- The average linear trend corresponds to about {abs(slope_per_year):.3f} seconds per year ({overall_trend['slope_per_day']:.6f} s/day). This suggests a {'substantial' if abs(slope_per_year)>1.0 else 'modest' if abs(slope_per_year)>0.1 else 'small'} yearly progression.")
            if pct is not None:
                yearly_pct = (pct / (( (datetime.fromisoformat(first_iso.replace('Z','+00:00')).timestamp()) and 1) )) if pct is not None else None
                # we don't compute a robust annualized percent, but provide contextual wording
                txt_lines.append(f"- In relative terms, this is about {abs(pct):.2f}% change over the full period; distributed evenly it's a small percent-per-year shift but may be concentrated in specific seasons or years.")
            txt_lines.append("- Interpretation: an overall reduction in mean lap time usually means the driver, car setup, or team performance improved, but the large spread (high CV) shows many sessions with different conditions — check for class changes, car/model changes, or outlier sessions that drive variance.")
            txt_lines.append("- Suggested next checks: review per-aggregated-name stats (variants of the name), inspect per-session means for outliers, and compare only sessions in the same class or year to isolate true driver-driven improvement.")
        except Exception:
            pass

    # write narrative summary to txtpath (already removed above if present)
    with open(txtpath, 'w', encoding='utf8') as tf:
        tf.write('\n'.join(txt_lines))
    print(f"Wrote narrative summary to {txtpath}")
    # Commentary: interpret the numbers briefly for users
    print('\nInterpretation:')
    print('- Percentile indicates the percent of drivers (in the selected cohort) that this driver is MORE variable than; higher percentile means comparatively MORE consistent')
    print("  (we compute percentile = 100*(total - rank)/total, so rank=1 -> ~100%.")
    print("- CV (coefficient of variation) = stdev/mean; lower CV means lap times are tighter relative to mean.")
    print("- MAD and median are robust measures; for drivers with multimodal lap distributions, median/MAD may be more informative than mean/CV.")
    print(f"- Sampled sessions: {len(session_keys)} session mappings were found for this aggregated name (shown above).")


if __name__ == '__main__':
    main()
