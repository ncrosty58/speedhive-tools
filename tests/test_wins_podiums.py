from speedhive.analyzers.analyze_results import (
    compute_wins_and_podiums,
    get_wins_podiums_rankings,
)


def _result(name, position_in_class, status="Normal"):
    return {"name": name, "positionInClass": position_in_class, "status": status}


def _session(session_type="race"):
    return {"name": "Session", "type": session_type}


def test_class_position_determines_win_and_podium():
    results_payloads = {
        "1": [
            _result("Jane Doe", 1),
            _result("John Roe", 2),
            _result("Amy Sue", 3),
            _result("Bob Lee", 4),
        ],
    }
    session_map = {"1": _session()}

    counts = compute_wins_and_podiums(results_payloads, session_map)
    assert counts["Jane Doe"]["wins"] == 1
    assert counts["Jane Doe"]["podiums"] == 1
    assert counts["John Roe"]["wins"] == 0
    assert counts["John Roe"]["podiums"] == 1
    assert counts["Amy Sue"]["podiums"] == 1
    assert counts["Bob Lee"]["wins"] == 0
    assert counts["Bob Lee"]["podiums"] == 0


def test_dns_excluded_from_starts_dnf_and_dq_counted_but_never_win():
    results_payloads = {
        "1": [
            _result("Jane Doe", 1, status="DNS"),
            _result("John Roe", 1, status="DNF"),
            _result("Amy Sue", 1, status="DQ"),
        ],
    }
    session_map = {"1": _session()}

    counts = compute_wins_and_podiums(results_payloads, session_map)
    assert "Jane Doe" not in counts  # DNS never even registers a start

    assert counts["John Roe"]["starts"] == 1
    assert counts["John Roe"]["wins"] == 0
    assert counts["John Roe"]["podiums"] == 0

    assert counts["Amy Sue"]["starts"] == 1
    assert counts["Amy Sue"]["wins"] == 0
    assert counts["Amy Sue"]["podiums"] == 0


def test_name_variants_merge_before_summing():
    results_payloads = {
        "1": [_result("Jane Doe", 1)],
        "2": [_result("  JANE   DOE  ", 1)],
        "3": [_result("Jane Doe", 2)],
    }
    session_map = {"1": _session(), "2": _session(), "3": _session()}

    most_wins, most_podiums = get_wins_podiums_rankings(results_payloads, session_map, min_starts=1)
    assert len(most_wins) == 1
    row = most_wins[0]
    assert row["wins"] == 2
    assert row["podiums"] == 3
    assert row["starts"] == 3


def test_min_starts_gate_excludes_low_sample_drivers():
    results_payloads = {
        "1": [_result("One Hit Wonder", 1)],
    }
    session_map = {"1": _session()}

    most_wins, most_podiums = get_wins_podiums_rankings(results_payloads, session_map, min_starts=3)
    assert most_wins == []
    assert most_podiums == []

    most_wins, _ = get_wins_podiums_rankings(results_payloads, session_map, min_starts=1)
    assert len(most_wins) == 1


def test_session_type_defaults_to_race_only():
    results_payloads = {
        "1": [_result("Jane Doe", 1)],
    }
    session_map = {"1": _session(session_type="qualifying")}

    counts = compute_wins_and_podiums(results_payloads, session_map)
    assert counts == {}

    counts = compute_wins_and_podiums(results_payloads, session_map, session_types=["qualifying"])
    assert counts["Jane Doe"]["wins"] == 1
