from speedhive.analyzers.analyze_class_pace import compute_participation_by_year


def _enriched_entry(name):
    return {"name": name, "driver_id": name, "lap_count": 10, "mean": 60.0}


def test_participation_counts_distinct_drivers_across_classes_once_per_year():
    enriched = {
        "session1_pos1": _enriched_entry("Jane Doe"),
        "session2_pos1": _enriched_entry("Jane Doe"),  # same driver, different class/session, same year
        "session1_pos2": _enriched_entry("John Smith"),
    }
    session_map = {
        "1": {"name": "Race 1", "type": "race", "startTime": "2024-05-01"},
        "2": {"name": "Race 2", "type": "race", "startTime": "2024-06-01"},
    }

    result = compute_participation_by_year(enriched, session_map)
    assert result["years"] == [2024]
    assert result["distinct_drivers"] == [2]


def test_participation_separates_years():
    enriched = {
        "session1_pos1": _enriched_entry("Jane Doe"),
        "session2_pos1": _enriched_entry("Jane Doe"),
    }
    session_map = {
        "1": {"name": "Race 1", "type": "race", "startTime": "2023-05-01"},
        "2": {"name": "Race 2", "type": "race", "startTime": "2024-05-01"},
    }

    result = compute_participation_by_year(enriched, session_map)
    assert result["years"] == [2023, 2024]
    assert result["distinct_drivers"] == [1, 1]


def test_participation_normalizes_near_duplicate_names():
    enriched = {
        "session1_pos1": _enriched_entry("Jane Doe"),
        "session1_pos2": _enriched_entry("  JANE   DOE  "),
    }
    session_map = {
        "1": {"name": "Race 1", "type": "race", "startTime": "2024-05-01"},
    }

    result = compute_participation_by_year(enriched, session_map)
    assert result["distinct_drivers"] == [1]


def test_participation_respects_session_type_filter():
    enriched = {
        "session1_pos1": _enriched_entry("Jane Doe"),
        "session2_pos1": _enriched_entry("John Smith"),
    }
    session_map = {
        "1": {"name": "Race 1", "type": "race", "startTime": "2024-05-01"},
        "2": {"name": "Qualifying 1", "type": "qualifying", "startTime": "2024-05-01"},
    }

    result = compute_participation_by_year(enriched, session_map, session_types=["race"])
    assert result["years"] == [2024]
    assert result["distinct_drivers"] == [1]

    result_all = compute_participation_by_year(enriched, session_map, session_types=["race", "qualifying"])
    assert result_all["distinct_drivers"] == [2]
