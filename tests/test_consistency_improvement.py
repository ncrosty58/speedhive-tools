from speedhive.analyzers.analyze_consistency import (
    aggregate_by_name_and_year,
    get_most_improved_rankings,
)


def _entry(session_id, pos, name, lap_count=25, mean=60.0, stdev=3.0):
    key = f"session{session_id}_pos{pos}"
    cv = stdev / mean if mean else None
    return key, {
        "name": name,
        "driver_id": key,
        "lap_count": lap_count,
        "mean": mean,
        "stdev": stdev,
        "cv": cv,
        "session_keys": [key],
    }


def _session(year, session_type="race"):
    return {"name": f"Session {year}", "type": session_type, "startTime": f"{year}-05-01"}


def test_most_improved_compares_first_and_last_year_not_second():
    enriched = dict([
        _entry(1, 1, "Jane Doe", lap_count=25, mean=60.0, stdev=6.0),   # 2020, CV=10%
        _entry(2, 1, "Jane Doe", lap_count=25, mean=60.0, stdev=4.8),   # 2022, CV=8%
        _entry(3, 1, "Jane Doe", lap_count=25, mean=60.0, stdev=3.0),   # 2024, CV=5%
    ])
    session_map = {
        "1": _session(2020),
        "2": _session(2022),
        "3": _session(2024),
    }

    most_improved, most_declined = get_most_improved_rankings(enriched, session_map, min_laps=20)
    assert len(most_improved) == 1
    row = most_improved[0]
    assert row["first_year"] == 2020
    assert row["last_year"] == 2024
    assert row["cv_delta"] > 0  # improved (CV went down)
    assert abs(row["cv_delta"] - 0.05) < 1e-9


def test_driver_with_single_qualifying_year_is_excluded():
    enriched = dict([
        _entry(1, 1, "Solo Driver", lap_count=25, mean=60.0, stdev=6.0),   # 2020, qualifies
        _entry(2, 1, "Solo Driver", lap_count=5, mean=60.0, stdev=3.0),    # 2021, too few laps
    ])
    session_map = {
        "1": _session(2020),
        "2": _session(2021),
    }

    most_improved, most_declined = get_most_improved_rankings(enriched, session_map, min_laps=20)
    names_improved = [r["name"] for r in most_improved]
    names_declined = [r["name"] for r in most_declined]
    assert "Solo Driver" not in names_improved
    assert "Solo Driver" not in names_declined


def test_name_variants_merge_before_year_bucketing():
    enriched = dict([
        _entry(1, 1, "Jane Doe", lap_count=30, mean=60.0, stdev=6.0),        # 2020, CV=10%, higher volume -> cluster rep
        _entry(2, 1, "  JANE   DOE  ", lap_count=25, mean=60.0, stdev=3.0),  # 2024, CV=5%, same person, different spelling
    ])
    session_map = {
        "1": _session(2020),
        "2": _session(2024),
    }

    most_improved, _ = get_most_improved_rankings(enriched, session_map, min_laps=20)
    assert len(most_improved) == 1
    row = most_improved[0]
    assert row["first_year"] == 2020
    assert row["last_year"] == 2024


def test_session_type_filtering():
    enriched = dict([
        _entry(1, 1, "Jane Doe", lap_count=25, mean=60.0, stdev=6.0),
        _entry(2, 1, "Jane Doe", lap_count=25, mean=60.0, stdev=3.0),
    ])
    session_map = {
        "1": _session(2020, session_type="qualifying"),
        "2": _session(2024, session_type="qualifying"),
    }

    # Restricting to "race" excludes both qualifying-only years -- nothing qualifies.
    most_improved, most_declined = get_most_improved_rankings(
        enriched, session_map, session_types=["race"], min_laps=20
    )
    assert most_improved == []
    assert most_declined == []

    # Asking for "qualifying" picks the sessions back up.
    most_improved, _ = get_most_improved_rankings(
        enriched, session_map, session_types=["qualifying"], min_laps=20
    )
    assert len(most_improved) == 1


def test_aggregate_by_name_and_year_buckets_by_year():
    enriched = dict([
        _entry(1, 1, "Jane Doe", lap_count=25, mean=60.0, stdev=6.0),
        _entry(2, 1, "Jane Doe", lap_count=25, mean=60.0, stdev=3.0),
    ])
    session_map = {
        "1": _session(2020),
        "2": _session(2024),
    }

    result = aggregate_by_name_and_year(enriched, session_map)
    assert set(result["Jane Doe"].keys()) == {2020, 2024}
    assert result["Jane Doe"][2020]["lap_count"] == 25
    assert result["Jane Doe"][2024]["lap_count"] == 25


def test_cluster_names_preserves_aggregate_cv():
    # A driver whose sessions have very different within-session stdevs:
    # the pooled stdev/mean is NOT the lap-weighted average of session CVs,
    # so cluster_names must carry the aggregate's cv through its re-pooling
    # instead of recomputing it from pooled stdev.
    from speedhive.analyzers.analyze_consistency import aggregate_by_name, cluster_names

    enriched = dict([
        _entry(1, 1, "Jane Doe", lap_count=10, mean=100.0, stdev=40.0),  # CV=40%
        _entry(2, 1, "Jane Doe", lap_count=90, mean=80.0, stdev=0.8),    # CV=1%
    ])
    session_map = {"1": _session(2020), "2": _session(2021)}

    by_name = aggregate_by_name(enriched, session_map)
    expected_cv = (10 * 0.40 + 90 * 0.01) / 100  # lap-weighted avg = 4.9%
    assert abs(by_name["Jane Doe"]["cv"] - expected_cv) < 1e-9

    clustered = cluster_names(by_name)
    assert abs(clustered["Jane Doe"]["cv"] - expected_cv) < 1e-9


def test_cluster_names_multi_alias_cv_is_lap_weighted_average():
    from speedhive.analyzers.analyze_consistency import aggregate_by_name, cluster_names

    enriched = dict([
        _entry(1, 1, "Jane Doe", lap_count=30, mean=100.0, stdev=30.0),      # CV=30%
        _entry(2, 1, "  JANE   DOE  ", lap_count=70, mean=80.0, stdev=1.6),  # CV=2%
    ])
    session_map = {"1": _session(2020), "2": _session(2021)}

    by_name = aggregate_by_name(enriched, session_map)
    clustered = cluster_names(by_name)
    assert len(clustered) == 1
    expected_cv = (30 * 0.30 + 70 * 0.02) / 100  # 10.4%
    assert abs(next(iter(clustered.values()))["cv"] - expected_cv) < 1e-9


def test_pool_weighted_stats_uses_carried_cv():
    from speedhive.analyzers.analyze_consistency import _pool_weighted_stats

    # 4-tuple parts: carried cv wins over stdev/mean recomputation
    pooled = _pool_weighted_stats([(10, 100.0, 40.0, 0.05), (10, 100.0, 40.0, 0.03)])
    assert abs(pooled["cv"] - 0.04) < 1e-9

    # 3-tuple parts keep the session-level stdev/mean behavior
    pooled = _pool_weighted_stats([(10, 100.0, 5.0), (10, 100.0, 3.0)])
    assert abs(pooled["cv"] - 0.04) < 1e-9
