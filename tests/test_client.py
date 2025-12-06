
# tests/test_client.py
"""
Tests for SpeedHiveClient using pytest and monkeypatch to avoid real HTTP calls.
"""
from __future__ import annotations
import io
import json
import os
import csv
import builtins
import types
from typing import Any, Dict, Optional
import pytest

from speedhive_tools.client import SpeedHiveClient, SpeedHiveAPIError
from speedhive_tools.models import TrackRecord, EventResult, Organization

# ----------------------- Helpers -----------------------
class StubResponse:
    """Minimal stub of requests.Response for testing."""
    def __init__(
        self,
        status_code: int = 200,
        json_data: Any = None,
        text: str = "",
        raise_json: bool = False,
    ):
        self.status_code = status_code
        self._json = json_data
        self.text = text or ""
        self._raise_json = raise_json
        # Provide a bytes payload like real requests.Response.content
        try:
            if self.text:
                self.content = self.text.encode("utf-8")
            elif json_data is not None:
                # If JSON is provided, serialize to bytes for content
                self.content = json.dumps(json_data).encode("utf-8")
            else:
                self.content = b""
        except Exception:
            # Fail-safe: ensure content always exists
            self.content = b""

    def json(self):
        if self._raise_json:
            raise ValueError("Invalid JSON")
        return self._json

def make_stub_request(expected_url_prefix: str, responses_by_url: Dict[str, StubResponse]):
    """
    Return a function to stub requests.Session.request.
    It looks up the URL in responses_by_url (exact match) and returns StubResponse.
    """
    def _stub_request(self, method: str, url: str, **kwargs):
        assert url.startswith(expected_url_prefix), f"Unexpected base URL: {url}"
        resp = responses_by_url.get(url)
        if not resp:
            # Default to 404 if URL not provided
            return StubResponse(status_code=404, json_data={"error": "not found"}, text="not found")
        return resp
    return _stub_request

# ----------------------- Fixtures -----------------------
@pytest.fixture
def client(monkeypatch):
    # Build client with a deterministic base URL for matching
    c = SpeedHiveClient(base_url="https://api.speedhive.com", timeout=3, retries=0)
    return c

# ----------------------- Tests: get_organization -----------------------
def test_get_organization_success(client, monkeypatch):
    org_id = 30476
    endpoint = f"https://api.speedhive.com/orgs/{org_id}"
    payload = {
        "org_id": org_id,
        "name": "Waterford Hills",
        "country": "US",
        "website": "https://waterfordhills.com",
    }
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(200, payload)},
        ),
    )
    org = client.get_organization(org_id)
    assert isinstance(org, Organization)
    assert org.org_id == org_id
    assert org.name == "Waterford Hills"
    assert org.country == "US"

def test_get_organization_http_error(client, monkeypatch):
    org_id = 99999
    endpoint = f"https://api.speedhive.com/orgs/{org_id}"
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(404, {"error": "not found"}, text="not found")},
        ),
    )
    with pytest.raises(SpeedHiveAPIError) as exc:
        client.get_organization(org_id)
    assert "HTTP 404" in str(exc.value)

# ----------------------- Tests: get_event_results -----------------------
def test_get_event_results_success(client, monkeypatch):
    event_id = 123456
    endpoint = f"https://api.speedhive.com/events/{event_id}/results"
    payload = {
        "event_id": event_id,
        "event_name": "Round 1",
        "track_name": "Waterford Hills",
        "start_date": "2025-05-01",
        "end_date": "2025-05-03",
        "records": [
            {
                "driver_name": "Jane Driver",
                "lap_time": 61.861,
                "track_name": "Waterford Hills",
                "date": "2025-05-02",
                "vehicle": "Swift 01",
                "class_name": "FA",
            }
        ],
    }
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(200, payload)},
        ),
    )
    result = client.get_event_results(event_id)
    assert isinstance(result, EventResult)
    assert result.event_id == event_id
    assert result.event_name == "Round 1"
    assert len(result.records) == 1
    assert isinstance(result.records[0], TrackRecord) or isinstance(result.records[0], dict)

def test_get_event_results_invalid_json(client, monkeypatch):
    event_id = 123456
    endpoint = f"https://api.speedhive.com/events/{event_id}/results"
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(200, None, raise_json=True)},
        ),
    )
    with pytest.raises(SpeedHiveAPIError) as exc:
        client.get_event_results(event_id)
    assert "Invalid JSON response" in str(exc.value)

# ----------------------- Tests: get_track_records_by_org -----------------------
def test_get_track_records_by_org_success(client, monkeypatch):
    org_id = 30476
    endpoint = f"https://api.speedhive.com/orgs/{org_id}/records"
    payload = {
        "records": [
            {
                "driver_name": "J. Lewis Cooper, Jr",
                "lap_time": 61.861,
                "track_name": "Waterford Hills",
                "date": "2009-05-10",
                "vehicle": "Swift 01 4A",
                "class_name": "FA",
            },
            {
                "driver_name": "Jane Driver",
                "lap_time": 62.001,
                "track_name": "Waterford Hills",
                "date": "2010-06-11",
                "vehicle": "Swift 02",
                "class_name": "FB",
            },
        ]
    }
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(200, payload)},
        ),
    )
    records = client.get_track_records_by_org(org_id)
    assert isinstance(records, list)
    assert len(records) == 2
    assert records[0].driver_name.startswith("J. Lewis")
    assert abs(records[0].lap_time - 61.861) < 1e-6

def test_get_track_records_by_org_raw_list(client, monkeypatch):
    """Support endpoints that return a raw list rather than a wrapped dict."""
    org_id = 30476
    endpoint = f"https://api.speedhive.com/orgs/{org_id}/records"
    payload = [
        {
            "driver_name": "Raw List Driver",
            "lap_time": 60.5,
            "track_name": "Waterford Hills",
            "date": "2021-01-01",
            "vehicle": None,
            "class_name": "FA",
        }
    ]
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(200, payload)},
        ),
    )
    records = client.get_track_records_by_org(org_id)
    assert len(records) == 1
    assert records[0].driver_name == "Raw List Driver"

def test_get_track_records_by_org_http_error(client, monkeypatch):
    org_id = 30476
    endpoint = f"https://api.speedhive.com/orgs/{org_id}/records"
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(500, {"error": "server"}, text="server error")},
        ),
    )
    with pytest.raises(SpeedHiveAPIError) as exc:
        client.get_track_records_by_org(org_id)
    assert "HTTP 500" in str(exc.value)

# ----------------------- Tests: pagination in list_organization_events -----------------------
def test_list_organization_events_paged_items_key(client, monkeypatch):
    org_id = 30476
    endpoint = f"https://api.speedhive.com/orgs/{org_id}/events"
    # Two pages via numeric page/totalPages
    page1 = {
        "page": 1,
        "totalPages": 2,
        "items": [
            {
                "event_id": 111,
                "event_name": "Event 111",
                "track_name": "WH",
                "start_date": "2025-04-01",
                "end_date": "2025-04-02",
                "records": [],
            }
        ],
    }
    page2 = {
        "page": 2,
        "totalPages": 2,
        "items": [
            {
                "event_id": 222,
                "event_name": "Event 222",
                "track_name": "WH",
                "start_date": "2025-05-01",
                "end_date": "2025-05-02",
                "records": [],
            }
        ],
    }
    calls = {"count": 0}
    def _stub(self, method: str, url: str, **kwargs):
        assert url.startswith("https://api.speedhive.com/")
        # Decide which page to return based on query params
        params = kwargs.get("params") or {}
        page = params.get("page", 1)
        calls["count"] += 1
        if page == 1:
            return StubResponse(200, page1)
        return StubResponse(200, page2)

    monkeypatch.setattr(type(client.session), "request", _stub)
    events = client.list_organization_events(org_id, per_page=1)
    assert len(events) == 2
    assert {e.event_id for e in events} == {111, 222}
    assert calls["count"] >= 2  # fetched both pages

def test_list_organization_events_items_missing_fallback(client, monkeypatch):
    org_id = 30476
    endpoint = f"https://api.speedhive.com/orgs/{org_id}/events"
    # Endpoint returns list directly (no "items" key)
    data = [
        {
            "event_id": 333,
            "event_name": "Event 333",
            "track_name": "WH",
            "start_date": "2025-06-01",
            "end_date": "2025-06-02",
            "records": [],
        }
    ]
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(200, data)},
        ),
    )
    events = client.list_organization_events(org_id, per_page=100)
    assert len(events) == 1
    assert events[0].event_id == 333

# ----------------------- Tests: export helpers -----------------------
def test_export_records_to_json(tmp_path, client):
    records = [
        TrackRecord(
            driver_name="Driver A",
            lap_time=61.861,
            track_name="WH",
            date="2025-01-01",
            vehicle="Swift",
            class_name="FA",
        )
    ]
    fp = tmp_path / "records.json"
    client.export_records_to_json(records, str(fp))
    assert fp.exists()
    data = json.loads(fp.read_text("utf-8"))
    assert "records" in data
    assert isinstance(data["records"], list)
    assert data["records"][0]["driver_name"] == "Driver A"

def test_export_records_to_csv(tmp_path, client):
    records = [
        TrackRecord(
            driver_name="Driver A",
            lap_time=61.861,
            track_name="WH",
            date="2025-01-01",
            vehicle="Swift",
            class_name="FA",
        ),
        TrackRecord(
            driver_name="Driver B",
            lap_time=62.000,
            track_name="WH",
            date="2025-01-02",
            vehicle=None,
            class_name="FB",
        ),
    ]
    fp = tmp_path / "records.csv"
    client.export_records_to_csv(records, str(fp))
    assert fp.exists()
    lines = fp.read_text("utf-8").splitlines()
    # Header + two rows
    assert len(lines) >= 3
    # Verify CSV columns include driver_name and lap_time
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    row = next(reader)
    assert "driver_name" in row or "driverName" in row  # depending on model field names
    assert "lap_time" in row or "lapTime" in row

# ----------------------- Edge cases -----------------------
def test_request_non_2xx_error_message_includes_body(client, monkeypatch):
    # Use a direct call to _request to verify error content
    endpoint = "orgs/invalid"
    url = f"https://api.speedhive.com/{endpoint}"
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {url: StubResponse(429, {"error": "rate limit"}, text="Too Many Requests")},
        ),
    )
    with pytest.raises(SpeedHiveAPIError) as exc:
        client._request("GET", endpoint)
    s = str(exc.value)
    assert "HTTP 429" in s
    assert "rate limit" in s or "Too Many Requests" in s

def test_invalid_json_parsing_raises(client, monkeypatch):
    endpoint = "orgs/30476"
    url = f"https://api.speedhive.com/{endpoint}"
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {url: StubResponse(200, None, raise_json=True)},
        ),
    )
    with pytest.raises(SpeedHiveAPIError) as exc:
        client._request("GET", endpoint)
    assert "Invalid JSON response" in str(exc.value)

# --- Lap data tests (NEW) ---
def test_get_session_lap_data_success_list(client, monkeypatch):
    session_id = 10998445
    position = 3
    endpoint = f"https://api.speedhive.com/sessions/{session_id}/lapdata/{position}/laps"
    payload = [
        {"lap": 1, "timeMs": 91234, "gapMs": None},
        {"lap": 2, "timeMs": 90567, "gapMs": 200},
    ]
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(200, payload)},
        ),
    )
    rows = client.get_session_lap_data(session_id, position)
    assert isinstance(rows, list)
    assert len(rows) == 2
    assert rows[0]["lap"] == 1

def test_get_session_lap_data_wrapped_dict(client, monkeypatch):
    session_id = 10998445
    position = 3
    endpoint = f"https://api.speedhive.com/sessions/{session_id}/lapdata/{position}/laps"
    payload = {"laps": [{"lap": 1, "timeMs": 91234}]}
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(200, payload)},
        ),
    )
    rows = client.get_session_lap_data(session_id, position)
    assert len(rows) == 1
    assert rows[0]["lap"] == 1

def test_get_session_lap_data_http_error(client, monkeypatch):
    session_id = 10998445
    position = 99
    endpoint = f"https://api.speedhive.com/sessions/{session_id}/lapdata/{position}/laps"
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(404, {"error": "not found"}, text="not found")},
        ),
    )
    with pytest.raises(SpeedHiveAPIError) as exc:
        client.get_session_lap_data(session_id, position)
    assert "HTTP 404" in str(exc.value)

def test_export_session_lapdata_to_ndjson(tmp_path, client, monkeypatch):
    session_id = 10998445
    position = 3
    endpoint = f"https://api.speedhive.com/sessions/{session_id}/lapdata/{position}/laps"
    payload = [
        {"lap": 1, "timeMs": 91234},
        {"lap": 2, "timeMs": 90567},
    ]
    monkeypatch.setattr(
        type(client.session),
        "request",
        make_stub_request(
            "https://api.speedhive.com/",
            {endpoint: StubResponse(200, payload)},
        ),
    )
    out_fp = tmp_path / "laps.ndjson"
    count = client.export_session_lapdata_to_ndjson(session_id, position, str(out_fp))
    assert count == 2
    lines = out_fp.read_text("utf-8").splitlines()
    assert len(lines) == 2
    obj = json.loads(lines[0])
    assert obj.get("lap") == 1
