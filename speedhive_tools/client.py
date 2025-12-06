
"""
client.py
Speedhive Event Results API Client (public endpoints; no authentication required).

Endpoints implemented (based on provided API examples):
- List events (across sport filters):
  GET /events?sport=All&sportCategory=Motorized&count=25&offset=0

- List events for an organization:
  GET /organizations/{ORG_ID}/events?count=25&offset=0&sportCategory=Motorized

- Get an event, optionally including sessions:
  GET /events/{EVENT_ID}?sessions=true

- List announcements (track records) for a session:
  GET /sessions/{SESSION_ID}/announcements

Design goals:
- Resilient HTTP (retries, timeouts, logging).
- Strong typing via Pydantic models (see models.py).
- Offset/count pagination helpers.
- Convenience traversal & export utilities.

"""

from __future__ import annotations

import csv
import json
import logging
from typing import Any, Dict, List, Optional, TypeVar, Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import (
    Event,
    EventsPage,
    Session,
    Announcement,
    AnnouncementsPage,
)


# ------------------------------------------------------------------------------
# Errors
# ------------------------------------------------------------------------------

class SpeedHiveAPIError(Exception):
    """Custom exception for Speedhive API errors."""
    pass


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://eventresults-api.speedhive.com/api/v0.2.3/eventresults"
DEFAULT_TIMEOUT = 15
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5
DEFAULT_USER_AGENT = "speedhive-tools/1.0 (+https://github.com/ncrosty58/speedhive-tools)"

ENDPOINTS = {
    "events": "events",
    "organization_events": "organizations/{org_id}/events",
    "event": "events/{event_id}",
    "session_announcements": "sessions/{session_id}/announcements",
}

T = TypeVar("T")


# ------------------------------------------------------------------------------
# Client
# ------------------------------------------------------------------------------

class SpeedHiveClient:
    """
    Client for the MYLAPS Speedhive Event Results API.

    Parameters
    ----------
    base_url : str
        Base URL (default points to v0.2.3 eventresults).
    timeout : int
        Request timeout (seconds).
    retries : int
        Total automatic retries for transient failures.
    backoff_factor : float
        Exponential backoff factor.
    user_agent : str
        User-Agent header value.
    extra_headers : Optional[Dict[str, str]]
        Any additional headers to include in all requests.
    logger : Optional[logging.Logger]
        A logger; if not provided, a module logger is used.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        user_agent: str = DEFAULT_USER_AGENT,
        extra_headers: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.session = self._build_session(
            retries=retries,
            backoff_factor=backoff_factor,
            user_agent=user_agent,
            extra_headers=extra_headers,
        )

    # --------------------------------------------------------------------------
    # Session / HTTP
    # --------------------------------------------------------------------------

    def _build_session(
        self,
        retries: int,
        backoff_factor: float,
        user_agent: str,
        extra_headers: Optional[Dict[str, str]],
    ) -> requests.Session:
        session = requests.Session()

        headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
        }
        if extra_headers:
            headers.update(extra_headers)
        session.headers.update(headers)

        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "HEAD", "OPTIONS"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Perform an HTTP request and parse JSON.

        Raises
        ------
        SpeedHiveAPIError on HTTP errors or invalid JSON.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        to = timeout or self.timeout

        self.logger.debug("Request %s %s params=%s", method, url, params)

        try:
            resp = self.session.request(method=method.upper(), url=url, params=params, timeout=to)
        except requests.RequestException as e:
            raise SpeedHiveAPIError(f"Network error: {e}") from e

        if not (200 <= resp.status_code < 300):
            # Try JSON, fall back to text
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            raise SpeedHiveAPIError(f"HTTP {resp.status_code} for {method} {url} | Response: {err}")

        try:
            data = resp.json()
        except ValueError as e:
            raise SpeedHiveAPIError(f"Invalid JSON response from {url}: {e}") from e

        self.logger.debug("Response (truncated): %s", str(data)[:1000])
        return data

    def _get(self, endpoint: str, *, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", endpoint, params=params)

    # --------------------------------------------------------------------------
    # Pagination (offset/count)
    # --------------------------------------------------------------------------

    def _paginate_offset_count(
        self,
        endpoint: str,
        *,
        base_params: Optional[Dict[str, Any]] = None,
        count: int = 25,
        offset: int = 0,
        parse_batch: Callable[[Dict[str, Any]], List[T]],
        max_items: Optional[int] = None,
    ) -> List[T]:
        """
        Generic offset/count pagination loop that uses a parser function
        to convert a raw page into typed items.
        """
        items: List[T] = []
        off = offset

        while True:
            params = dict(base_params or {})
            params.update({"count": count, "offset": off})

            data = self._get(endpoint, params=params)
            batch = parse_batch(data)  # list[T]

            if not batch:
                break

            items.extend(batch)
            if max_items is not None and len(items) >= max_items:
                items = items[:max_items]
                break

            # If fewer than requested, we've hit the last page
            if len(batch) < count:
                break

            off += count

        return items

    # --------------------------------------------------------------------------
    # API Methods
    # --------------------------------------------------------------------------

    # 1) List events across sport filters --------------------------------------

    def list_events(
        self,
        *,
        sport: str = "All",
        sport_category: str = "Motorized",
        count: int = 25,
        offset: int = 0,
        max_items: Optional[int] = None,
    ) -> List[Event]:
        """
        List events across sport filters.

        Endpoint:
            GET /events?sport={sport}&sportCategory={sport_category}&count={count}&offset={offset}
        """
        def parse_batch(data: Dict[str, Any]) -> List[Event]:
            # Normalize via page wrapper (handles items/events/raw list)
            page = EventsPage.model_validate(data)
            return page.items

        base_params = {"sport": sport, "sportCategory": sport_category}
        return self._paginate_offset_count(
            ENDPOINTS["events"],
            base_params=base_params,
            count=count,
            offset=offset,
            parse_batch=parse_batch,
            max_items=max_items,
        )

    # 2) List events for an organization ---------------------------------------

    def list_events_by_organization(
        self,
        org_id: int,
        *,
        count: int = 25,
        offset: int = 0,
        sport_category: str = "Motorized",
        max_items: Optional[int] = None,
    ) -> List[Event]:
        """
        List all events belonging to an organization.

        Endpoint:
            GET /organizations/{ORG_ID}/events?count={count}&offset={offset}&sportCategory={sport_category}
        """
        endpoint = ENDPOINTS["organization_events"].format(org_id=org_id)

        def parse_batch(data: Dict[str, Any]) -> List[Event]:
            page = EventsPage.model_validate(data)
            return page.items

        base_params = {"sportCategory": sport_category}
        return self._paginate_offset_count(
            endpoint,
            base_params=base_params,
            count=count,
            offset=offset,
            parse_batch=parse_batch,
            max_items=max_items,
        )

    # 3) Get an event (optionally with sessions) --------------------------------

    def get_event(self, event_id: int, *, include_sessions: bool = False) -> Event:
        """
        Fetch a single event. If include_sessions=True, sessions are included.

        Endpoint:
            GET /events/{EVENT_ID}
            GET /events/{EVENT_ID}?sessions=true
        """
        endpoint = ENDPOINTS["event"].format(event_id=event_id)
        params = {"sessions": "true"} if include_sessions else None
        data = self._get(endpoint, params=params)
        return Event.model_validate(data)

    def get_event_with_sessions(self, event_id: int) -> Event:
        """
        Convenience wrapper for get_event(..., include_sessions=True).
        """
        return self.get_event(event_id, include_sessions=True)

    def list_sessions_from_event(self, event_id: int) -> List[Session]:
        """
        Fetch an event and return its sessions.
        """
        event = self.get_event_with_sessions(event_id)
        return event.sessions or []

    # 4) List session announcements (track records) -----------------------------

    def list_session_announcements(self, session_id: int) -> List[Announcement]:
        """
        List announcements (aka track records) for a session.

        Endpoint:
            GET /sessions/{SESSION_ID}/announcements
        """
        endpoint = ENDPOINTS["session_announcements"].format(session_id=session_id)
        data = self._get(endpoint)
        page = AnnouncementsPage.model_validate(data)
        return page.items

    # --------------------------------------------------------------------------
    # Convenience traversal (org → events → sessions → announcements)
    # --------------------------------------------------------------------------

    def fetch_org_announcements(
        self,
        org_id: int,
        *,
        count_events: int = 25,
        offset_events: int = 0,
        max_events: Optional[int] = None,
        max_sessions_per_event: Optional[int] = None,
    ) -> Dict[int, List[Announcement]]:
        """
        Traverse all events for an organization, then sessions, then announcements.

        Returns
        -------
        dict[int, list[Announcement]]
            Mapping of session_id → announcements.
        """
        result: Dict[int, List[Announcement]] = {}

        events = self.list_events_by_organization(
            org_id,
            count=count_events,
            offset=offset_events,
            max_items=max_events,
        )

        for ev in events:
            ev_id = ev.resolved_id
            if not ev_id:
                continue

            sessions = self.list_sessions_from_event(ev_id)
            if max_sessions_per_event is not None:
                sessions = sessions[:max_sessions_per_event]

            for s in sessions:
                sid = s.resolved_id
                if not sid:
                    continue
                anns = self.list_session_announcements(sid)
                result[sid] = anns

        return result

    # --------------------------------------------------------------------------
    # Export Utilities
    # --------------------------------------------------------------------------

    @staticmethod
    def export_announcements_to_json(announcements: List[Announcement], file_path: str) -> None:
        """
        Export announcements to JSON:
            { "announcements": [ {...}, {...} ] }
        """
        payload = {"announcements": [a.model_dump() for a in announcements]}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    @staticmethod
    def export_announcements_to_csv(announcements: List[Announcement], file_path: str) -> None:
        """
        Export announcements to CSV. Headers are inferred from model fields.
        """
        rows = [a.model_dump() for a in announcements]
        headers = sorted({k for r in rows for k in r.keys()}) if rows else ["id", "session_id", "event_id", "title", "message", "class_abbreviation", "driver_name", "lap_time_seconds", "date", "track_name"]

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)


# ------------------------------------------------------------------------------
# Optional quick demo (safe to remove in production)
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    client = SpeedHiveClient()

    try:
        # Example flow: org → events → sessions → announcements
        ORG_ID = 30476  # Waterford Hills (example)
        ann_map = client.fetch_org_announcements(
            ORG_ID,
            count_events=25,
            offset_events=0,
            max_events=5,
            max_sessions_per_event=5,
        )
        total_anns = sum(len(v) for v in ann_map.values())
        print(f"Fetched announcements across {len(ann_map)} sessions (total={total_anns}).")

        # If you want to export a single session's announcements:
        if ann_map:
            some_session_id, anns = next(iter(ann_map.items()))
            client.export_announcements_to_json(anns, f"session_{some_session_id}_announcements.json")
            client.export_announcements_to_csv(anns, f"session_{some_session_id}_announcements.csv")
            print(f"Exported {len(anns)} announcements for session {some_session_id}.")
    except SpeedHiveAPIError as e:
        print(f"Error: {e}")
