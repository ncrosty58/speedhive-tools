"""Tests for the SpeedhiveClient wrapper."""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add mylaps_client to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "mylaps_client"))

from mylaps_client_wrapper import SpeedhiveClient


class TestSpeedhiveClientInit:
    """Test SpeedhiveClient initialization."""

    def test_default_init(self):
        client = SpeedhiveClient()
        assert client.base_url == "https://api2.mylaps.com"
        assert client.token is None
        assert client.timeout == 30.0

    def test_custom_base_url(self):
        client = SpeedhiveClient(base_url="https://custom.api.com")
        assert client.base_url == "https://custom.api.com"

    def test_with_token(self):
        client = SpeedhiveClient(token="test_token")
        assert client.token == "test_token"


class TestSpeedhiveClientMethods:
    """Test SpeedhiveClient methods exist and have proper signatures."""

    def test_has_get_organization_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_organization")
        assert callable(client.get_organization)

    def test_has_get_events_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_events")
        assert callable(client.get_events)

    def test_has_iter_events_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "iter_events")
        assert callable(client.iter_events)

    def test_has_get_event_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_event")
        assert callable(client.get_event)

    def test_has_get_sessions_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_sessions")
        assert callable(client.get_sessions)

    def test_has_get_session_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_session")
        assert callable(client.get_session)

    def test_has_get_laps_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_laps")
        assert callable(client.get_laps)

    def test_has_get_results_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_results")
        assert callable(client.get_results)

    def test_has_get_announcements_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_announcements")
        assert callable(client.get_announcements)

    def test_has_get_lap_chart_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_lap_chart")
        assert callable(client.get_lap_chart)

    def test_has_get_championships_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_championships")
        assert callable(client.get_championships)

    def test_has_get_championship_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_championship")
        assert callable(client.get_championship)

    def test_has_get_server_time_method(self):
        client = SpeedhiveClient()
        assert hasattr(client, "get_server_time")
        assert callable(client.get_server_time)


class TestSpeedhiveClientParseResponse:
    """Test response parsing logic."""

    def test_parse_response_with_empty_content(self):
        client = SpeedhiveClient()
        mock_response = Mock()
        mock_response.content = None
        result = client._parse_response(mock_response)
        assert result is None

    def test_parse_response_with_json_list(self):
        client = SpeedhiveClient()
        mock_response = Mock()
        mock_response.content = b'[{"id": 1}, {"id": 2}]'
        result = client._parse_response(mock_response)
        assert result == [{"id": 1}, {"id": 2}]

    def test_parse_response_with_json_dict(self):
        client = SpeedhiveClient()
        mock_response = Mock()
        mock_response.content = b'{"name": "test", "value": 123}'
        result = client._parse_response(mock_response)
        assert result == {"name": "test", "value": 123}


class TestExtractEventsToCSV:
    """Test the events extractor."""

    def test_extract_events_to_csv_exists(self):
        p = Path("examples/processing/extract_events_to_csv.py")
        assert p.exists(), "extract_events_to_csv.py should exist"

    def test_extract_events_has_main(self):
        p = Path("examples/processing/extract_events_to_csv.py")
        src = p.read_text(encoding="utf8")
        assert "def main(" in src


