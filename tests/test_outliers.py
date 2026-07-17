
from speedhive.utils.lap_analysis import filter_outlier_laps, compute_lap_statistics
from speedhive.analyzers.analyze_consistency import get_consistency_rankings

def test_filter_outlier_laps():
    # Less than 4 laps, should return unchanged
    laps_short = [50.0, 51.0, 52.0]
    assert filter_outlier_laps(laps_short) == laps_short

    # Normal laps with one extreme slow outlier (e.g. pit stop or crash).
    # Median = 51.0, cutoff = 1.30 * 51.0 = 66.3
    laps = [50.0, 51.0, 52.0, 50.0, 51.0, 52.0, 120.0]
    filtered = filter_outlier_laps(laps)
    assert 120.0 not in filtered
    assert len(filtered) == 6

    # Short interrupted race: 3 of 10 laps under caution. The old IQR fence
    # absorbed these (quartiles get dragged up); the median rule must not.
    caution_race = [78.3, 78.4, 78.5, 78.6, 78.8, 79.0, 83.1, 149.4, 185.2, 187.7]
    filtered = filter_outlier_laps(caution_race)
    assert filtered == [78.3, 78.4, 78.5, 78.6, 78.8, 79.0, 83.1]

    # Implausibly fast lap (timing glitch / missed loop) is dropped too
    glitch = [30.0, 80.0, 80.5, 81.0, 80.2]
    assert 30.0 not in filter_outlier_laps(glitch)

    # All identical laps
    laps_same = [50.0, 50.0, 50.0, 50.0]
    assert filter_outlier_laps(laps_same) == laps_same

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


def test_dedupe_session_ids():
    from speedhive.utils.lap_analysis import dedupe_session_ids

    laps_a = [{"position": 1, "laps": [{"lapNumber": 1, "lapTime": "50.0"}]}]
    results_a = [{"name": "Jane Doe", "position": 1}]
    # same event synced twice: identical laps payloads under two session ids
    keep = dedupe_session_ids(
        {"100": results_a, "200": list(results_a), "300": [{"name": "Bob", "position": 1}]},
        {"100": laps_a, "200": list(laps_a), "300": [{"position": 1, "laps": [{"lapNumber": 1, "lapTime": "61.0"}]}]},
    )
    assert keep == {"100", "300"}

    # duplicate laps win over trivially differing results (real dup pairs exist
    # whose results diverge in minor fields while lap data is byte-identical)
    keep = dedupe_session_ids(
        {"100": results_a, "200": [{"name": "Jane Doe", "position": 1, "isQualified": True}]},
        {"100": laps_a, "200": list(laps_a)},
    )
    assert keep == {"100"}

    # no laps: fall back to results equality
    keep = dedupe_session_ids({"100": results_a, "200": list(results_a)}, {})
    assert keep == {"100"}

    # empty payloads are never treated as duplicates of each other
    keep = dedupe_session_ids({"100": [], "200": []}, {})
    assert keep == {"100", "200"}


def test_first_lap_and_duplicates_excluded_from_enriched():
    from speedhive.utils.lap_analysis import _compute_laps_and_enriched_from_payloads

    def lap_rows(times):
        return [{"position": 1, "laps": [
            {"lapNumber": i + 1, "lapTime": str(t)} for i, t in enumerate(times)
        ]}]

    sessions = {"1": {"name": "Race 1", "type": "race"}, "2": {"name": "Race 1", "type": "race"}}
    results = {
        "1": [{"name": "Jane Doe", "position": 1}],
        "2": [{"name": "Jane Doe", "position": 1}],
    }
    # session 2 is a byte-identical duplicate of session 1
    laps = {
        "1": lap_rows([55.0, 50.0, 50.2, 50.4, 50.6]),
        "2": lap_rows([55.0, 50.0, 50.2, 50.4, 50.6]),
    }

    laps_by_driver, enriched = _compute_laps_and_enriched_from_payloads(sessions, results, laps)

    # duplicate session dropped entirely
    assert "session2_pos1" not in enriched
    # standing-start lap 1 (55.0) excluded from collected laps
    assert laps_by_driver["session1_pos1"] == [50.0, 50.2, 50.4, 50.6]
    assert enriched["session1_pos1"]["lap_count"] == 4
