"""Tests for compute_driver_directory (the all-drivers stats table payload)."""
from speedhive.analyzers.analyze_results import compute_driver_directory


def _row(name, status="Normal", pos_in_class=None):
    row = {"name": name, "status": status}
    if pos_in_class is not None:
        row["positionInClass"] = pos_in_class
    return row


SESSION_MAP = {
    "1": {"name": "Race 1", "type": "race"},
    "2": {"name": "Race 2", "type": "race"},
    "3": {"name": "Practice 1", "type": "practice"},
}


def test_counts_starts_wins_podiums_and_ranks():
    results = {
        "1": [
            _row("Alice Fast", pos_in_class=1),
            _row("Bob Steady", pos_in_class=2),
            _row("Cara Slow", pos_in_class=4),
        ],
        "2": [
            _row("Alice Fast", pos_in_class=1),
            _row("Bob Steady", pos_in_class=3),
        ],
    }
    payload = compute_driver_directory(results, SESSION_MAP)

    assert payload["total_drivers"] == 3

    alice = next(d for d in payload["drivers"] if d["name"] == "Alice Fast")
    assert alice["starts"] == 2
    assert alice["wins"] == 2
    assert alice["podiums"] == 2
    assert alice["win_pct"] == 100.0
    assert alice["starts_rank"] == 1
    assert alice["wins_rank"] == 1

    bob = next(d for d in payload["drivers"] if d["name"] == "Bob Steady")
    assert bob["starts"] == 2
    assert bob["wins"] == 0
    assert bob["podiums"] == 2

    cara = next(d for d in payload["drivers"] if d["name"] == "Cara Slow")
    assert cara["starts"] == 1
    assert cara["podiums"] == 0
    assert cara["starts_rank"] == 3


def test_dns_rows_and_non_race_sessions_are_ignored():
    results = {
        "1": [
            _row("Alice Fast", pos_in_class=1),
            _row("Dana DNS", status="DNS", pos_in_class=2),
        ],
        "3": [
            _row("Practice Pete", pos_in_class=1),
        ],
    }
    payload = compute_driver_directory(results, SESSION_MAP)
    names = [d["name"] for d in payload["drivers"]]
    assert "Dana DNS" not in names
    assert "Practice Pete" not in names
    assert payload["total_drivers"] == 1


def test_dnf_counts_start_but_not_result():
    results = {
        "1": [
            _row("Alice Fast", pos_in_class=2),
            _row("Danny DNF", status="DNF", pos_in_class=1),
        ],
    }
    payload = compute_driver_directory(results, SESSION_MAP)
    danny = next(d for d in payload["drivers"] if d["name"] == "Danny DNF")
    assert danny["starts"] == 1
    assert danny["wins"] == 0
    assert danny["podiums"] == 0


def test_spelling_variants_collapse_with_most_frequent_display_name():
    results = {
        "1": [_row("Andrew T Abbott", pos_in_class=1)],
        "2": [_row("andrew t abbott", pos_in_class=2)],
    }
    payload = compute_driver_directory(results, SESSION_MAP)
    assert payload["total_drivers"] == 1
    row = payload["drivers"][0]
    assert row["starts"] == 2
    assert row["wins"] == 1
    # Tie on frequency: deterministic pick (longer/greater string wins the tie)
    assert row["name"] in ("Andrew T Abbott", "andrew t abbott")


def test_rank_ties_are_deterministic():
    results = {
        "1": [
            _row("Zed Same", pos_in_class=5),
            _row("Amy Same", pos_in_class=6),
        ],
    }
    p1 = compute_driver_directory(results, SESSION_MAP)
    p2 = compute_driver_directory(results, SESSION_MAP)
    assert [d["starts_rank"] for d in p1["drivers"]] == [d["starts_rank"] for d in p2["drivers"]]
    # Same starts count: tie broken by normalized name ascending
    amy = next(d for d in p1["drivers"] if d["name"] == "Amy Same")
    zed = next(d for d in p1["drivers"] if d["name"] == "Zed Same")
    assert amy["starts_rank"] < zed["starts_rank"]
