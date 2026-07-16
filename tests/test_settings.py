import json
import os

from speedhive.settings import (
    get_bulk_parser_for_org,
    get_org_env_var,
    get_org_env_var_override,
    get_org_env_var_with_source,
    get_parsing_engine,
    get_stats_min_laps,
    has_global_default,
    org_settings_path,
    read_org_settings,
    set_org_env_var,
    write_org_settings,
)


def _use_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SPEEDHIVE_DATA_DIR", str(tmp_path))


def test_get_org_env_var_prefers_override_over_global(monkeypatch, tmp_path):
    _use_data_dir(monkeypatch, tmp_path)
    monkeypatch.delenv("SOME_KEY", raising=False)
    monkeypatch.delenv("SOME_KEY_42", raising=False)

    assert get_org_env_var("SOME_KEY", 42) is None
    assert get_org_env_var_override("SOME_KEY", 42) is None
    assert has_global_default("SOME_KEY") is False

    monkeypatch.setenv("SOME_KEY", "global-value")
    assert get_org_env_var("SOME_KEY", 42) == "global-value"
    assert get_org_env_var_override("SOME_KEY", 42) is None
    assert has_global_default("SOME_KEY") is True

    write_org_settings(42, {"overrides": {"SOME_KEY": "org-value"}})
    assert get_org_env_var("SOME_KEY", 42) == "org-value"
    assert get_org_env_var_override("SOME_KEY", 42) == "org-value"
    # a different org is unaffected
    assert get_org_env_var("SOME_KEY", 99) == "global-value"
    assert get_org_env_var_override("SOME_KEY", 99) is None


def test_get_org_env_var_falls_back_to_scoped_env_var_without_settings_file(monkeypatch, tmp_path):
    _use_data_dir(monkeypatch, tmp_path)
    monkeypatch.delenv("SOME_KEY", raising=False)
    monkeypatch.setenv("SOME_KEY_42", "scoped-env-value")

    assert get_org_env_var_override("SOME_KEY", 42) == "scoped-env-value"
    assert get_org_env_var("SOME_KEY", 42) == "scoped-env-value"


def test_get_org_env_var_with_source(monkeypatch, tmp_path):
    _use_data_dir(monkeypatch, tmp_path)
    monkeypatch.delenv("SOME_KEY", raising=False)

    assert get_org_env_var_with_source("SOME_KEY", 42) == (None, None)

    monkeypatch.setenv("SOME_KEY", "global-value")
    assert get_org_env_var_with_source("SOME_KEY", 42) == ("global-value", "global")

    write_org_settings(42, {"overrides": {"SOME_KEY": "org-value"}})
    assert get_org_env_var_with_source("SOME_KEY", 42) == ("org-value", "org")


def test_set_org_env_var_persists_and_updates_process_env(monkeypatch, tmp_path):
    _use_data_dir(monkeypatch, tmp_path)
    monkeypatch.delenv("SOME_KEY_42", raising=False)

    set_org_env_var("SOME_KEY", 42, "org-value")
    assert os.environ["SOME_KEY_42"] == "org-value"

    path = org_settings_path(42)
    assert path.exists()
    with open(path) as f:
        saved = json.load(f)
    assert saved["overrides"]["SOME_KEY"] == "org-value"

    # Clearing removes the key from both the file and the process env, and
    # drops the now-empty "overrides" block entirely.
    set_org_env_var("SOME_KEY", 42, None)
    assert "SOME_KEY_42" not in os.environ
    with open(path) as f:
        saved = json.load(f)
    assert "overrides" not in saved


def test_read_org_settings_missing_or_invalid_file_returns_empty_dict(tmp_path, monkeypatch):
    _use_data_dir(monkeypatch, tmp_path)
    assert read_org_settings(1234) == {}

    path = org_settings_path(1234)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not valid json")
    assert read_org_settings(1234) == {}


def test_get_parsing_engine_defaults_to_regex(monkeypatch, tmp_path):
    _use_data_dir(monkeypatch, tmp_path)
    assert get_parsing_engine(42) == "regex"

    write_org_settings(42, {"parsing": {"engine": "llm"}})
    assert get_parsing_engine(42) == "llm"

    write_org_settings(42, {"parsing": {"engine": "something-unrecognized"}})
    assert get_parsing_engine(42) == "regex"


def test_get_bulk_parser_for_org_none_unless_llm_configured(monkeypatch, tmp_path):
    _use_data_dir(monkeypatch, tmp_path)
    assert get_bulk_parser_for_org(42) is None

    write_org_settings(42, {"parsing": {"engine": "llm"}})
    parser = get_bulk_parser_for_org(42)
    assert parser is not None
    assert parser.keywords.get("org_id") == 42


def test_get_stats_min_laps_default_and_override(monkeypatch, tmp_path):
    _use_data_dir(monkeypatch, tmp_path)
    assert get_stats_min_laps(42) == 20

    write_org_settings(42, {"stats": {"min_laps": 5}})
    assert get_stats_min_laps(42) == 5
