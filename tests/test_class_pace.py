from speedhive.analyzers.analyze_class_pace import (
    compute_participation_by_class_year,
    compute_participation_by_year,
)


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


def _result_row(position, result_class):
    return {"position": position, "resultClass": result_class}


def test_participation_by_class_averages_only_years_the_class_ran():
    # GT ran both years (3 then 1 participants -> avg 2); FV ran only one
    # year (2 participants) -- FV's average should be 2, not 1, since the
    # year it didn't run shouldn't drag its average down.
    enriched = {
        "session1_pos1": _enriched_entry("A"),
        "session1_pos2": _enriched_entry("B"),
        "session1_pos3": _enriched_entry("C"),
        "session2_pos1": _enriched_entry("D"),
        "session2_pos2": _enriched_entry("E"),
        "session2_pos3": _enriched_entry("F"),
    }
    session_map = {
        "1": {"name": "Race 1", "type": "race", "startTime": "2023-05-01"},
        "2": {"name": "Race 2", "type": "race", "startTime": "2024-05-01"},
    }
    results_map = {
        "1": [_result_row(1, "GT"), _result_row(2, "GT"), _result_row(3, "GT")],
        "2": [_result_row(1, "GT"), _result_row(2, "FV"), _result_row(3, "FV")],
    }

    result = compute_participation_by_class_year(enriched, session_map, results_map, max_classes=None)
    gt_idx = result["classes"].index("GT")
    fv_idx = result["classes"].index("FV")
    assert result["avg_participants"][gt_idx] == 2.0  # (3 + 1) / 2
    assert result["avg_participants"][fv_idx] == 2.0  # 2 / 1, not 2 / 2

    assert result["years_by_class"]["FV"] == [2024]
    assert result["participants_by_class"]["FV"] == [2]


def test_participation_by_class_ranked_and_capped():
    enriched = {
        "session1_pos1": _enriched_entry("A"),
        "session1_pos2": _enriched_entry("B"),
        "session1_pos3": _enriched_entry("C"),
    }
    session_map = {"1": {"name": "Race 1", "type": "race", "startTime": "2024-05-01"}}
    results_map = {
        "1": [_result_row(1, "GT"), _result_row(2, "GT"), _result_row(3, "FV")],
    }

    result = compute_participation_by_class_year(enriched, session_map, results_map, max_classes=1)
    assert result["classes"] == ["GT"]
    assert result["avg_participants"] == [2.0]
