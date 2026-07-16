import json

from speedhive.workflows.track_records import curation
from speedhive.stores import track_records as store
from speedhive.ndjson import dumps_ndjson, load_ndjson, parse_ndjson_lines, save_ndjson


def test_ndjson_roundtrip(tmp_path):
    doc = {"date": "2026-07-15", "records": [{"a": 1}, {"b": 2}]}
    path = tmp_path / "x.ndjson"
    save_ndjson(path, doc, "records")

    lines = path.read_text().strip().splitlines()
    assert json.loads(lines[0]) == {"_meta": {"date": "2026-07-15"}}
    assert len(lines) == 3

    loaded = load_ndjson(path, {"date": None, "records": []}, "records")
    assert loaded == doc


def test_ndjson_no_meta_line_when_no_meta():
    body = dumps_ndjson({"rejected": [{"x": 1}]}, "rejected")
    lines = body.strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"x": 1}
    assert parse_ndjson_lines(lines, "rejected") == {"rejected": [{"x": 1}]}


def test_ndjson_missing_file_returns_fresh_default(tmp_path):
    default = {"date": None, "records": []}
    loaded = load_ndjson(tmp_path / "missing.ndjson", default, "records")
    loaded["records"].append({"a": 1})
    # the shared default must not be mutated
    assert default["records"] == []


def test_legacy_json_migrates_to_ndjson(tmp_path):
    """Old pretty-printed curated.json files must transparently become NDJSON."""
    legacy_doc = {"date": "2026-03-01", "records": [
        {"classAbbreviation": "FA", "lapTime": "1:01.861", "driverName": "J. Lewis Cooper, Jr", "marque": "Swift", "date": "2009-05-10"},
        {"classAbbreviation": "GT1", "lapTime": "1:05.5", "driverName": "X", "marque": None, "date": "2019-06-01"},
    ]}
    p = curation.paths_for_org(tmp_path, 999)
    p["dir"].mkdir(parents=True)
    (p["dir"] / "curated.json").write_text(json.dumps(legacy_doc))

    loaded = curation.load_curated(p)
    assert loaded["date"] == "2026-03-01"
    assert len(loaded["records"]) == 2

    # ndjson now exists, legacy renamed aside
    assert p["curated"].exists()
    assert not (p["dir"] / "curated.json").exists()
    assert (p["dir"] / "curated.json.migrated").exists()

    # round-trip through save/load preserves everything
    loaded["date"] = "2026-07-15"
    curation.save_curated(p, loaded)
    again = curation.load_curated(p)
    assert again["date"] == "2026-07-15"
    assert again["records"] == loaded["records"]


def test_track_record_store_helpers_round_trip(tmp_path):
    p = store.paths_for_org(tmp_path, 999)
    assert p["curated"].name == "curated.ndjson"
    assert p["rejected"].name == "rejected.ndjson"

    payload = {"enabled": True, "de_duplicate": False}
    config_path = p["dir"] / "config.json"
    store.save_json(config_path, payload)
    assert store.load_json(config_path, {}) == payload


def test_lap_time_to_seconds_is_strict():
    assert curation.lap_time_to_seconds("1:13.325") == 73.325
    assert curation.lap_time_to_seconds("63.004") == 63.004
    assert curation.lap_time_to_seconds("not-a-time") is None
    assert curation.lap_time_to_seconds(None) is None


def test_normalize_classification_aliases_and_review():
    alias_map = {"aliases": {"spec miata": "SM"}, "always_review": ["F5"]}
    assert curation.normalize_classification("Spec Miata", alias_map) == ("ok", "SM")
    assert curation.normalize_classification("f5", alias_map) == ("ambiguous", None)
    assert curation.normalize_classification("IT7", alias_map) == ("ok", "IT7")


def test_delete_curated_record_normalization(tmp_path):
    p = curation.paths_for_org(tmp_path, 999)
    p["dir"].mkdir(parents=True)

    # 1. Populate curated with a record that has None/""/mixed-case driverName
    curated_doc = {
        "date": "2026-07-16",
        "records": [
            {
                "classAbbreviation": "fa",
                "lapTime": "1:01.861",
                "driverName": None,
                "marque": "Swift",
                "date": "2026-07-16",
                "source": "speedhive"
            },
            {
                "classAbbreviation": "SM",
                "lapTime": "1:22.456",
                "driverName": "John Doe",
                "marque": "Mazda",
                "date": "2026-07-16",
                "source": "speedhive"
            }
        ]
    }
    curation.save_curated(p, curated_doc)

    # Delete first record using identity with empty string "" for driverName (how UI form behaves)
    identity_1 = ("FA", "1:01.861", "", "2026-07-16")
    res_1 = curation.delete_curated_record(p, identity_1)
    assert res_1["found"] is True
    assert res_1["permanent"] is False

    # Delete second record with mismatched case for driverName
    identity_2 = ("sm", "1:22.456", "JOHN DOE", "2026-07-16")
    res_2 = curation.delete_curated_record(p, identity_2)
    assert res_2["found"] is True

    # 2. Check rejected contains both
    rejected = curation.load_rejected(p).get("rejected", [])
    assert len(rejected) == 2

    # 3. Verify make_ldc behaves as expected for checks
    rejected_ldc = {
        curation.make_ldc(r.get("classAbbreviation"), r.get("lapTime"), r.get("driverName"))
        for r in rejected
    }
    raw_ldc_1 = curation.make_ldc("FA", "1:01.861", None)
    assert raw_ldc_1 in rejected_ldc

    raw_ldc_2 = curation.make_ldc("SM", "1:22.456", "john doe")
    assert raw_ldc_2 in rejected_ldc


def _seed_single_curated_record(tmp_path, org_id=999, **overrides):
    p = curation.paths_for_org(tmp_path, org_id)
    p["dir"].mkdir(parents=True)
    record = {
        "classAbbreviation": "FA",
        "lapTime": "1:02.500",
        "driverName": "Jane Doe",
        "marque": "Swift",
        "date": "2026-07-01",
        "source": "speedhive",
    }
    record.update(overrides)
    curation.save_curated(p, {"date": "2026-07-01", "records": [record]})
    return p


def test_edit_curated_record_appends_edit_history_entry(tmp_path):
    p = _seed_single_curated_record(tmp_path)
    identity = ("FA", "1:02.500", "Jane Doe", "2026-07-01")

    updated = curation.edit_curated_record(p, identity, {
        "classAbbreviation": "FA",
        "lapTime": "1:01.861",
        "driverName": "Jane Doe",
        "marque": "Swift",
        "date": "2026-07-01",
    })

    assert updated["modified"] is True
    assert len(updated["edit_history"]) == 1
    entry = updated["edit_history"][0]
    assert entry["fields"] == {"lapTime": {"from": "1:02.500", "to": "1:01.861"}}
    assert entry["changed_at"] == updated["modified_at"]


def test_edit_curated_record_sequential_edits_are_not_cumulative(tmp_path):
    p = _seed_single_curated_record(tmp_path)
    identity = ("FA", "1:02.500", "Jane Doe", "2026-07-01")

    first = curation.edit_curated_record(p, identity, {
        "classAbbreviation": "FA",
        "lapTime": "1:01.861",
        "driverName": "Jane Doe",
        "marque": "Swift",
        "date": "2026-07-01",
    })
    new_identity = ("FA", "1:01.861", "Jane Doe", "2026-07-01")
    second = curation.edit_curated_record(p, new_identity, {
        "classAbbreviation": "FA",
        "lapTime": "1:01.861",
        "driverName": "John Doe",
        "marque": "Swift",
        "date": "2026-07-01",
    })

    assert first["classAbbreviation"] == second["classAbbreviation"]  # same logical record, matched again by its new identity
    history = second["edit_history"]
    assert len(history) == 2
    assert history[0]["fields"] == {"lapTime": {"from": "1:02.500", "to": "1:01.861"}}
    assert history[1]["fields"] == {"driverName": {"from": "Jane Doe", "to": "John Doe"}}


def test_edit_curated_record_noop_edit_does_not_append_empty_entry(tmp_path):
    p = _seed_single_curated_record(tmp_path)
    identity = ("FA", "1:02.500", "Jane Doe", "2026-07-01")

    updated = curation.edit_curated_record(p, identity, {
        "classAbbreviation": "FA",
        "lapTime": "1:02.500",
        "driverName": "Jane Doe",
        "marque": "Swift",
        "date": "2026-07-01",
    })

    assert updated["modified"] is True  # unconditional flag refresh is unchanged
    assert "edit_history" not in updated


def test_edit_curated_record_manual_source_never_gets_modified_or_history(tmp_path):
    p = _seed_single_curated_record(tmp_path, source="manual")
    identity = ("FA", "1:02.500", "Jane Doe", "2026-07-01")

    updated = curation.edit_curated_record(p, identity, {
        "classAbbreviation": "FA",
        "lapTime": "1:01.861",
        "driverName": "Jane Doe",
        "marque": "Swift",
        "date": "2026-07-01",
    })

    assert "modified" not in updated
    assert "edit_history" not in updated


def test_lap_times_match_tolerates_format_and_rounding():
    # curated "0:59.439" vs raw announcer "59.439" (no leading "0:")
    assert curation.lap_times_match("0:59.439", "59.439") is True
    # hand-transcription rounding, within the 0.01s tolerance
    assert curation.lap_times_match("1:06.897", "1:06.896") is True
    # genuinely different times must not match
    assert curation.lap_times_match("1:11.501", "1:12.190") is False
    # unparseable input never matches
    assert curation.lap_times_match("not-a-time", "1:06.896") is False
    assert curation.lap_times_match(None, "1:06.896") is False


def test_driver_names_match_tolerates_missing_middle_name():
    assert curation.driver_names_match("Andrew Abbott", "Andrew Thomas Abbott") is True
    assert curation.driver_names_match("Andrew Abbott", "Andrew T Abbott") is True
    # exact match (post-normalization) still matches
    assert curation.driver_names_match("john doe", "John Doe") is True
    # different first or last name must not match
    assert curation.driver_names_match("Steve Ives", "Steven Ives") is False
    assert curation.driver_names_match("Andrew Abbott", "Andrew Smith") is False
    # empty/missing names never match
    assert curation.driver_names_match("", "Andrew Abbott") is False
    assert curation.driver_names_match(None, None) is False


def test_records_match_normalized_requires_exact_class():
    assert curation.records_match_normalized(
        "FV", "1:13.101", "Andrew Abbott",
        "FV", "1:13.099", "Andrew Thomas Abbott",
    ) is True
    # same lap/driver but a different class is not the same record
    assert curation.records_match_normalized(
        "FV", "1:13.101", "Andrew Abbott",
        "FP", "1:13.101", "Andrew Abbott",
    ) is False


def test_dedupe_curated_speedhive_additions_catches_format_variants(tmp_path):
    """The exact-string dedupe historically missed duplicates that differ
    only in lap-time format or a middle name/initial -- see
    NEXT_SESSION_PLAN.md item 1. Covers both the original exact-match case
    and the newer normalized-tolerance case in one pass."""
    p = curation.paths_for_org(tmp_path, 999)
    p["dir"].mkdir(parents=True)

    curated_doc = {
        "date": "2026-07-16",
        "records": [
            # Exact-match duplicate (different date only) -- the original bug.
            {"classAbbreviation": "GT3", "lapTime": "1:11.501", "driverName": "Paul Young",
             "marque": "Ford Probe", "date": "2020-06-28", "source": "manual"},
            {"classAbbreviation": "GT3", "lapTime": "1:11.501", "driverName": "Paul Young",
             "marque": None, "date": "2020-06-27", "source": "speedhive"},

            # Lap-time-format duplicate: "0:59.439" (curated) vs "59.439" (speedhive raw).
            {"classAbbreviation": "P1", "lapTime": "0:59.439", "driverName": "Jonathan Finstrom",
             "marque": "Staudacher S08", "date": "2021-05-27", "source": "manual"},
            {"classAbbreviation": "P1", "lapTime": "59.439", "driverName": "Jonathan Finstrom",
             "marque": None, "date": "2021-05-27", "source": "speedhive"},

            # Middle-name duplicate: curated omits the middle name the raw announcement has.
            {"classAbbreviation": "FV", "lapTime": "1:12.563", "driverName": "Andrew Abbott",
             "marque": "Vector AM-1", "date": "2019-08-04", "source": "manual"},
            {"classAbbreviation": "FV", "lapTime": "1:12.563", "driverName": "Andrew Thomas Abbott",
             "marque": None, "date": "2019-08-03", "source": "speedhive"},

            # Not a duplicate -- different class -- must survive untouched.
            {"classAbbreviation": "FP", "lapTime": "1:12.563", "driverName": "Andrew Abbott",
             "marque": None, "date": "2019-08-05", "source": "speedhive"},
        ],
    }
    curation.save_curated(p, curated_doc)

    result = curation.dedupe_curated_speedhive_additions(p)
    assert result["removed"] == 3
    assert {r["classAbbreviation"] for r in result["removed_records"]} == {"GT3", "P1", "FV"}
    assert all(r["source"] == "speedhive" for r in result["removed_records"])

    remaining = curation.load_curated(p)["records"]
    assert len(remaining) == 4
    assert {(r["classAbbreviation"], r["source"]) for r in remaining} == {
        ("GT3", "manual"), ("P1", "manual"), ("FV", "manual"), ("FP", "speedhive"),
    }

