"""Tests for the SpeedhiveClient wrapper."""
import pytest
from unittest.mock import Mock

from speedhive.client import AuthenticatedClient, Client
from speedhive.wrapper import SpeedhiveClient


class TestSpeedhiveClientInit:
    """Test SpeedhiveClient initialization."""

    def test_default_init(self):
        sc = SpeedhiveClient.create()
        assert isinstance(sc.client, Client)
        assert sc.client.base_url == "https://api2.mylaps.com"

    def test_custom_base_url(self):
        sc = SpeedhiveClient.create(base_url="https://custom.api.com")
        assert sc.client.base_url == "https://custom.api.com"

    def test_with_token(self):
        sc = SpeedhiveClient.create(token="test_token")
        assert isinstance(sc.client, AuthenticatedClient)
        assert sc.client.token == "test_token"


class TestSpeedhiveClientMethods:
    """Test SpeedhiveClient methods exist and have proper signatures."""

    def test_has_get_organization_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_organization")
        assert callable(sc.get_organization)

    def test_has_get_events_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_events")
        assert callable(sc.get_events)

    def test_has_iter_events_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "iter_events")
        assert callable(sc.iter_events)

    def test_has_get_event_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_event")
        assert callable(sc.get_event)

    def test_has_get_sessions_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_sessions")
        assert callable(sc.get_sessions)

    def test_has_get_session_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_session")
        assert callable(sc.get_session)

    def test_has_get_laps_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_laps")
        assert callable(sc.get_laps)

    def test_has_get_results_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_results")
        assert callable(sc.get_results)

    def test_has_get_announcements_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_announcements")
        assert callable(sc.get_announcements)

    def test_has_get_lap_chart_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_lap_chart")
        assert callable(sc.get_lap_chart)

    def test_has_get_championships_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_championships")
        assert callable(sc.get_championships)

    def test_has_get_championship_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_championship")
        assert callable(sc.get_championship)

    def test_has_get_server_time_method(self):
        sc = SpeedhiveClient.create()
        assert hasattr(sc, "get_server_time")
        assert callable(sc.get_server_time)


class TestSpeedhiveClientParseResponse:
    """Test response parsing logic."""

    def test_parse_response_with_empty_content(self):
        mock_response = Mock()
        mock_response.content = None
        result = SpeedhiveClient._parse_response(mock_response)
        assert result is None

    def test_parse_response_with_json_list(self):
        mock_response = Mock()
        mock_response.content = b'[{"id": 1}, {"id": 2}]'
        result = SpeedhiveClient._parse_response(mock_response)
        assert result == [{"id": 1}, {"id": 2}]

    def test_parse_response_with_json_dict(self):
        mock_response = Mock()
        mock_response.content = b'{"name": "test", "value": 123}'
        result = SpeedhiveClient._parse_response(mock_response)
        assert result == {"name": "test", "value": 123}


class TestExtractEventsToCSV:
    """Test the events extractor."""

    def test_extract_events_to_csv_exists(self):
        import importlib

        modname = "speedhive.processing.extract_events_to_csv"
        try:
            importlib.import_module(modname)
        except Exception as exc:  # pragma: no cover - test should fail if import fails
            pytest.fail(f"Could not import {modname}: {exc}")

    def test_extract_events_has_main(self):
        import importlib
        import inspect

        mod = importlib.import_module("speedhive.processing.extract_events_to_csv")
        # ensure at least the module exposes a callable main or extract function
        assert (hasattr(mod, "main") and inspect.isfunction(mod.main)) or hasattr(mod, "extract")
