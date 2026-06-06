import pytest
from pathlib import Path
import tempfile
import gzip
import json
import statistics

from speedhive.processing.process_lap_analysis import filter_outliers_iqr, compute_laps_and_enriched, compute_lap_statistics
from speedhive.analyzers.analyze_consistency import get_consistency_rankings

def test_filter_outliers_iqr():
    # Less than 4 laps, should return unchanged
    laps_short = [50.0, 51.0, 52.0]
    assert filter_outliers_iqr(laps_short) == laps_short

    # Normal laps with one extreme slow outlier (e.g. pit stop or crash)
    # Q1 = 50.5, Q3 = 51.5, IQR = 1.0. Upper bound = 51.5 + 1.5 * 1.0 = 53.0
    laps = [50.0, 51.0, 52.0, 50.0, 51.0, 52.0, 120.0]
    filtered = filter_outliers_iqr(laps)
    assert 120.0 not in filtered
    assert len(filtered) == 6
    assert all(x < 53.0 for x in filtered)

    # All identical laps
    laps_same = [50.0, 50.0, 50.0, 50.0]
    assert filter_outliers_iqr(laps_same) == laps_same

def test_compute_lap_statistics_outliers():
    # 5 normal laps, 1 outlier (150 seconds)
    laps = [
        {"lapTime": "50.0"},
        {"lapTime": "50.5"},
        {"lapTime": "51.0"},
        {"lapTime": "50.2"},
        {"lapTime": "50.8"},
        {"lapTime": "2:30.0"} # 150.0s
    ]
    # Without ignoring outliers
    stats_with = compute_lap_statistics(laps, ignore_outliers=False)
    assert stats_with["lap_count"] == 6
    
    # With ignoring outliers
    stats_without = compute_lap_statistics(laps, ignore_outliers=True)
    assert stats_without["lap_count"] == 5
    assert "2:30.0" not in stats_without["mean"]

def test_get_consistency_rankings():
    clustered = {
        "Driver A": {"lap_count": 20, "mean": 50.0, "stdev": 0.5, "cv": 0.01, "aliases": ["Driver A"]},
        "Driver B": {"lap_count": 25, "mean": 52.0, "stdev": 2.6, "cv": 0.05, "aliases": ["Driver B"]},
        "Driver C": {"lap_count": 5, "mean": 51.0, "stdev": 0.1, "cv": 0.002, "aliases": ["Driver C"]}, # below min_laps
    }
    
    top, least, total_drivers, total_laps = get_consistency_rankings(clustered, min_laps=10, limit=5)
    
    # Total drivers should include Driver C as well
    assert total_drivers == 3
    assert total_laps == 50
    
    # Ranks filtered by min_laps=10
    assert len(top) == 2
    assert top[0]["name"] == "Driver A" # lowest CV (0.01 < 0.05)
    assert least[0]["name"] == "Driver B" # highest CV (0.05 > 0.01)
