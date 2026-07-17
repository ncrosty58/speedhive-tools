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

    result = compute_participation_by_class_year(enriched, session_map, results_map, max_classes=None, min_years_active=1)
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

    result = compute_participation_by_class_year(enriched, session_map, results_map, max_classes=1, min_years_active=1)
    assert result["classes"] == ["GT"]
    assert result["avg_participants"] == [2.0]


def test_participation_by_class_merges_aliases():
    # "Spec Miata" and "SM" are the same class under the org's alias map --
    # without it they'd be two separate, smaller-looking classes.
    enriched = {
        "session1_pos1": _enriched_entry("A"),
        "session1_pos2": _enriched_entry("B"),
        "session2_pos1": _enriched_entry("C"),
    }
    session_map = {
        "1": {"name": "Race 1", "type": "race", "startTime": "2023-05-01"},
        "2": {"name": "Race 2", "type": "race", "startTime": "2024-05-01"},
    }
    results_map = {
        "1": [_result_row(1, "Spec Miata"), _result_row(2, "Spec Miata")],
        "2": [_result_row(1, "SM")],
    }
    alias_map = {"aliases": {"SPEC MIATA": "SM"}, "always_review": []}

    without_alias = compute_participation_by_class_year(enriched, session_map, results_map, max_classes=None, min_years_active=1)
    assert sorted(without_alias["classes"]) == ["SM", "Spec Miata"]

    with_alias = compute_participation_by_class_year(
        enriched, session_map, results_map, max_classes=None, alias_map=alias_map, min_years_active=1
    )
    # Merged into one group -- "Spec Miata" wins as the display label since
    # it's the more common raw spelling (2 entries vs SM's 1), same
    # frequency-based heuristic used for whitespace/case-only variants.
    assert with_alias["classes"] == ["Spec Miata"]
    assert with_alias["avg_participants"] == [1.5]  # (2 + 1) / 2
    assert with_alias["years_by_class"]["Spec Miata"] == [2023, 2024]
    assert with_alias["participants_by_class"]["Spec Miata"] == [2, 1]


def test_participation_by_class_min_years_active_excludes_one_off_classes():
    # "GT" ran 3 consecutive years with modest turnout; "SPECIAL" ran once
    # with a big one-off turnout. Without a years-active floor, SPECIAL's
    # higher single-year average would outrank GT despite GT being the
    # class that actually runs every year.
    enriched = {
        "session1_pos1": _enriched_entry("A"),
        "session1_pos2": _enriched_entry("B"),
        "session2_pos1": _enriched_entry("C"),
        "session2_pos2": _enriched_entry("D"),
        "session3_pos1": _enriched_entry("E"),
        "session3_pos2": _enriched_entry("F"),
        "session4_pos1": _enriched_entry("G"),
        "session4_pos2": _enriched_entry("H"),
        "session4_pos3": _enriched_entry("I"),
        "session4_pos4": _enriched_entry("J"),
    }
    session_map = {
        "1": {"name": "Race 1", "type": "race", "startTime": "2022-05-01"},
        "2": {"name": "Race 2", "type": "race", "startTime": "2023-05-01"},
        "3": {"name": "Race 3", "type": "race", "startTime": "2024-05-01"},
        "4": {"name": "Race 4", "type": "race", "startTime": "2024-06-01"},
    }
    results_map = {
        "1": [_result_row(1, "GT"), _result_row(2, "GT")],
        "2": [_result_row(1, "GT"), _result_row(2, "GT")],
        "3": [_result_row(1, "GT"), _result_row(2, "GT")],
        "4": [_result_row(1, "SPECIAL"), _result_row(2, "SPECIAL"), _result_row(3, "SPECIAL"), _result_row(4, "SPECIAL")],
    }

    result = compute_participation_by_class_year(enriched, session_map, results_map, max_classes=None)
    assert result["classes"] == ["GT"]
    assert "SPECIAL" not in result["classes"]

    # Raising the bar with a permissive floor lets SPECIAL back in, and it
    # does outrank GT on raw average (4 > 2) once eligible.
    result_permissive = compute_participation_by_class_year(
        enriched, session_map, results_map, max_classes=None, min_years_active=1
    )
    assert result_permissive["classes"][0] == "SPECIAL"
    assert "GT" in result_permissive["classes"]


def test_participation_by_class_always_review_tokens_stay_ungrouped():
    enriched = {
        "session1_pos1": _enriched_entry("A"),
        "session2_pos1": _enriched_entry("B"),
    }
    session_map = {
        "1": {"name": "Race 1", "type": "race", "startTime": "2023-05-01"},
        "2": {"name": "Race 2", "type": "race", "startTime": "2024-05-01"},
    }
    results_map = {
        "1": [_result_row(1, "F5")],
        "2": [_result_row(1, "F5")],
    }
    alias_map = {"aliases": {}, "always_review": ["F5"]}

    result = compute_participation_by_class_year(
        enriched, session_map, results_map, max_classes=None, alias_map=alias_map, min_years_active=1
    )
    # Still grouped by its own folded spelling (not dropped, not merged with
    # anything else) -- ambiguous just means "don't guess an alias for it."
    assert result["classes"] == ["F5"]
    assert result["avg_participants"] == [1.0]  # 1 driver/year, both years
