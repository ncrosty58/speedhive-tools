import json

from speedhive.utils.llm_track_records import (
    parse_track_record_text_llm,
    parse_track_record_texts_llm_bulk,
)
from speedhive.storage import SpeedhiveStorage


def _fake_call(response):
    def call(prompt, schema):
        return response
    return call


def test_parse_track_record_text_llm_found():
    result = parse_track_record_text_llm(
        "New Track Record (1:01.861) for FA by Bob.",
        _fake_call({
            "is_record": True,
            "classification": "FA",
            "lap_time": "1:01.861",
            "driver": "Bob",
            "marque": "Swift",
        }),
    )
    assert result["classification"] == "FA"
    assert result["lap_time_seconds"] == 61.861
    assert result["marque"] == "Swift"
    assert result["llm_uncertain"] is False


def test_parse_track_record_text_llm_not_a_record():
    result = parse_track_record_text_llm(
        "Checkered flag for session 3.",
        _fake_call({"is_record": False}),
    )
    assert result is None


def test_parse_track_record_text_llm_low_confidence_still_returned():
    result = parse_track_record_text_llm(
        "New record maybe? unclear.",
        _fake_call({
            "is_record": True,
            "low_confidence": True,
            "classification": "GT3",
            "lap_time": "1:10.000",
            "driver": "Someone",
        }),
    )
    assert result is not None
    assert result["llm_uncertain"] is True


def test_parse_track_record_text_llm_missing_field_is_uncertain():
    """A missing classification/lap_time is itself unreliable, even if the
    model didn't set low_confidence -- not dropped, so it's still visible
    (run_sync_and_diff routes it to rejected rather than losing it)."""
    result = parse_track_record_text_llm(
        "New Track Record for FA by Bob.",
        _fake_call({
            "is_record": True,
            "classification": "FA",
            "lap_time": "",
            "driver": "Bob",
        }),
    )
    assert result is not None
    assert result["llm_uncertain"] is True


def test_parse_track_record_text_llm_empty_text_short_circuits():
    def call(prompt, schema):
        raise AssertionError("should not call the LLM for empty text")
    assert parse_track_record_text_llm("", call) is None
    assert parse_track_record_text_llm("   ", call) is None


def test_bulk_parse_sparse_results_aligned_by_index():
    texts = [
        "New Track Record (1:01.861) for FA by Bob.",
        "Checkered flag.",
        "New Lap Record GT2: 1:10.935 by Carl.",
    ]

    def call(prompt, schema):
        assert "[0]" in prompt and "[1]" in prompt and "[2]" in prompt
        return {
            "results": [
                {"index": 0, "classification": "FA", "lap_time": "1:01.861", "driver": "Bob"},
                {"index": 2, "classification": "GT2", "lap_time": "1:10.935", "driver": "Carl"},
            ]
        }

    results = parse_track_record_texts_llm_bulk(texts, call)
    assert len(results) == 3
    assert results[1] is None
    assert results[0]["classification"] == "FA"
    assert results[2]["lap_time_seconds"] == 70.935


def test_bulk_parse_ignores_out_of_range_or_malformed_indices():
    def call(prompt, schema):
        return {"results": [
            {"index": 99, "classification": "FA", "lap_time": "1:00.000"},
            {"index": "not-an-int", "classification": "FA", "lap_time": "1:00.000"},
            "not-a-dict",
        ]}

    results = parse_track_record_texts_llm_bulk(["one text"], call)
    assert results == [None]


def test_bulk_parse_empty_input_makes_no_call():
    def call(prompt, schema):
        raise AssertionError("should not call the LLM for an empty text list")
    assert parse_track_record_texts_llm_bulk([], call) == []


def _seed_announcement(storage, org_id, session_id, event_id, texts_with_ts):
    with storage.connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (session_id, event_id, org_id, name, session_type, payload, saved_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (session_id, event_id, org_id, "Race 1", "race", "{}", "2026-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO events (event_id, org_id, name, starts_at, payload, saved_at) VALUES (?,?,?,?,?,?)",
            (event_id, org_id, "Event 1", "2026-01-01", "{}", "2026-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO session_announcements (session_id, event_id, org_id, payload, saved_at) VALUES (?,?,?,?,?)",
            (session_id, event_id, org_id, json.dumps(texts_with_ts), "2026-01-01T00:00:00Z"),
        )
        conn.commit()


def test_get_track_records_parse_cache_only_calls_bulk_parser_for_new_announcements(tmp_path):
    storage = SpeedhiveStorage(tmp_path / "test.db")
    org_id = 1
    _seed_announcement(storage, org_id, session_id=100, event_id=1, texts_with_ts=[
        {"text": "New Track Record (1:01.861) for FA by Bob.", "timestamp": "2026-01-01"},
        {"text": "Checkered flag.", "timestamp": "2026-01-01"},
    ])

    call_count = {"n": 0}

    def fake_bulk(texts):
        call_count["n"] += 1
        return [
            {"classification": "FA", "lap_time": "1:01.861", "lap_time_seconds": 61.861,
             "driver": "Bob", "marque": None, "llm_uncertain": False} if "FA" in t else None
            for t in texts
        ]

    cache = {}
    updates = {}
    records = storage.get_track_records(
        org_id, bulk_parser=fake_bulk, parse_cache=cache,
        on_parsed=lambda k, v: updates.update({k: v}),
    )
    assert call_count["n"] == 1
    assert len(records) == 1
    cache.update(updates)

    # Re-scanning with a warm cache and no new announcements must not call
    # the (expensive) bulk parser again, and must still return the same
    # complete result -- this is what keeps repeat scans/auto-rescans cheap.
    records_again = storage.get_track_records(
        org_id, bulk_parser=fake_bulk, parse_cache=cache, on_parsed=lambda k, v: None,
    )
    assert call_count["n"] == 1
    assert records_again == records

    # Adding one genuinely new announcement should only send that one text
    # through the bulk parser, while the cached one is served from cache.
    _seed_announcement(storage, org_id, session_id=100, event_id=1, texts_with_ts=[
        {"text": "New Track Record (1:01.861) for FA by Bob.", "timestamp": "2026-01-01"},
        {"text": "Checkered flag.", "timestamp": "2026-01-01"},
        {"text": "New Track Record (1:10.000) for GT2 by Bob FA style.", "timestamp": "2026-01-02"},
    ])
    seen_texts = []
    def counting_bulk(texts):
        seen_texts.extend(texts)
        return fake_bulk(texts)

    records_third = storage.get_track_records(
        org_id, bulk_parser=counting_bulk, parse_cache=cache, on_parsed=lambda k, v: None,
    )
    assert len(seen_texts) == 1
    assert len(records_third) == 2
