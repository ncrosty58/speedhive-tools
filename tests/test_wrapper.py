import json
from unittest.mock import patch, MagicMock

import pytest

from speedhive.client import Client
from speedhive.wrapper import SpeedhiveClient


class FakeResponse:
    def __init__(self, content):
        self.content = content


@pytest.fixture
def client():
    return Client(base_url="https://api.example.com")


def test_get_events_list(client):
    events = [
        {"id": 1, "name": "Event A"},
        {"id": 2, "name": "Event B"},
    ]
    response = FakeResponse(json.dumps(events).encode())
    with patch(
        "speedhive.wrapper.get_event_list.sync_detailed",
        return_value=response,
    ) as mock_get:
        sc = SpeedhiveClient(client)
        result = sc.get_events(org_id=30476, limit=2)
        assert result == events
        mock_get.assert_called_once_with(id=30476, client=client, offset=0, count=2)


def test_get_events_dict_response(client):
    # Some APIs return a dict with 'rows'
    response = FakeResponse(json.dumps({"rows": [{"id": 1}]}).encode())
    with patch(
        "speedhive.wrapper.get_event_list.sync_detailed",
        return_value=response,
    ):
        sc = SpeedhiveClient(client)
        result = sc.get_events(org_id=30476)
        assert result == [{"id": 1}]


def test_get_sessions_with_groups(client):
    session_data = {
        "groups": [
            {
                "sessions": [
                    {"id": 10, "name": "Practice"},
                    {"id": 11, "name": "Race"},
                ]
            }
        ]
    }
    response = FakeResponse(json.dumps(session_data).encode())
    with patch(
        "speedhive.wrapper.get_session_list.sync_detailed",
        return_value=response,
    ):
        sc = SpeedhiveClient(client)
        sessions = sc.get_sessions(event_id=100)
        assert len(sessions) == 2
        assert sessions[0]["id"] == 10


def test_get_laps_flatten(client):
    lap_data = [
        {
            "competitorId": 5,
            "position": 1,
            "laps": [
                {"lap": 1, "lapTime": "1:10.5", "speed": 90},
                {"lap": 2, "lapTime": "1:11.2", "speed": 89},
            ],
        }
    ]
    response = FakeResponse(json.dumps(lap_data).encode())
    with patch(
        "speedhive.wrapper.get_all_lap_times.sync_detailed",
        return_value=response,
    ):
        sc = SpeedhiveClient(client)
        laps = sc.get_laps(session_id=200, flatten=True)
        assert len(laps) == 2
        assert laps[0]["competitorId"] == 5
        assert laps[0]["lapNumber"] == 1
        assert laps[0]["lapTime"] == "1:10.5"


def test_get_track_records(client):
    # Mock iter_events and get_sessions, get_announcements
    with patch.object(
        SpeedhiveClient,
        "iter_events",
        return_value=[{"id": 1, "name": "EventX"}],
    ), patch.object(
        SpeedhiveClient,
        "get_sessions",
        return_value=[{"id": 100, "name": "SessionX"}],
    ), patch.object(
        SpeedhiveClient,
        "get_announcements",
        return_value=[
            {
                "text": "New Track Record (1:17.870) for IT7 by Bob Cross.",
                "timestamp": "2025-01-01T00:00:00Z",
            }
        ],
    ), patch(
        "speedhive.wrapper.parse_track_record_text",
        return_value={
            "classification": "IT7",
            "lap_time": "1:17.870",
            "lap_time_seconds": 77.87,
            "driver": "Bob Cross",
            "marque": None,
        },
    ):
        sc = SpeedhiveClient(client)
        records = sc.get_track_records(org_id=30476)
        assert len(records) == 1
        assert records[0]["classification"] == "IT7"
