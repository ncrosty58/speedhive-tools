"""User-friendly wrapper around the generated MyLaps API client.

This module provides a simple, Pythonic interface to the MyLaps Event Results API.
Instead of dealing with raw HTTP responses and JSON parsing, you get clean methods
that return typed dictionaries or lists.

Example usage:
    from mylaps_client_wrapper import SpeedhiveClient

    client = SpeedhiveClient()

    # Get events for an organization
    events = client.get_events(org_id=30476, limit=10)
    for event in events:
        print(f"{event['name']} - {event['date']}")

    # Get lap times for a session
    laps = client.get_laps(session_id=12345)
    for lap in laps:
        print(f"Lap {lap.get('lapNumber')}: {lap.get('lapTime')}")
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from event_results_client import Client, AuthenticatedClient
from event_results_client.api.system_time_controller import get_time as time_api
from event_results_client.api.organization_controller import get_event_list, get_organization
from event_results_client.api.event_controller import get_event, get_session_list
from event_results_client.api.session_controller import (
    get_all_lap_times,
    get_classification,
    get_announcements,
    get_session,
)


@dataclass
class SpeedhiveClient:
    """User-friendly client for the MyLaps Speedhive API.

    Args:
        base_url: API base URL (default: https://api2.mylaps.com)
        token: Optional API token for authenticated endpoints
        timeout: Request timeout in seconds (default: 30)

    Example:
        >>> client = SpeedhiveClient()
        >>> events = client.get_events(org_id=30476)
        >>> print(events[0]['name'])
    """

    base_url: str = "https://api2.mylaps.com"
    token: Optional[str] = None
    timeout: float = 30.0
    _client: Client = field(init=False, repr=False)

    def __post_init__(self):
        if self.token:
            self._client = AuthenticatedClient(
                base_url=self.base_url,
                token=self.token,
                timeout=self.timeout,
            )
        else:
            self._client = Client(
                base_url=self.base_url,
                timeout=self.timeout,
            )

    def _parse_response(self, response) -> Any:
        """Parse API response content as JSON."""
        if not response.content:
            return None
        return json.loads(response.content)

    # -------------------------------------------------------------------------
    # Organization endpoints
    # -------------------------------------------------------------------------

    def get_organization(self, org_id: int) -> Optional[Dict[str, Any]]:
        """Get organization details by ID.

        Args:
            org_id: Organization ID

        Returns:
            Organization dict with keys like 'id', 'name', 'country', etc.
        """
        response = get_organization.sync_detailed(id=org_id, client=self._client)
        return self._parse_response(response)

    def get_events(
        self,
        org_id: int,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get events for an organization.

        Args:
            org_id: Organization ID
            limit: Maximum number of events to return (default: API default)
            offset: Number of events to skip for pagination

        Returns:
            List of event dicts with keys like 'id', 'name', 'date', 'sessions', etc.
        """
        kwargs = {"id": org_id, "client": self._client, "offset": offset}
        if limit is not None:
            kwargs["count"] = limit
        response = get_event_list.sync_detailed(**kwargs)
        result = self._parse_response(response)
        return result if isinstance(result, list) else []

    def iter_events(
        self,
        org_id: int,
        page_size: int = 100,
    ) -> Iterator[Dict[str, Any]]:
        """Iterate over all events for an organization (handles pagination).

        Args:
            org_id: Organization ID
            page_size: Number of events per API request

        Yields:
            Event dicts one at a time
        """
        offset = 0
        while True:
            events = self.get_events(org_id=org_id, limit=page_size, offset=offset)
            if not events:
                break
            yield from events
            if len(events) < page_size:
                break
            offset += page_size

    # -------------------------------------------------------------------------
    # Event endpoints
    # -------------------------------------------------------------------------

    def get_event(self, event_id: int, include_sessions: bool = False) -> Optional[Dict[str, Any]]:
        """Get event details by ID.

        Args:
            event_id: Event ID
            include_sessions: Whether to include session list in response

        Returns:
            Event dict with keys like 'id', 'name', 'date', 'organization', etc.
        """
        response = get_event.sync_detailed(
            id=event_id,
            client=self._client,
            sessions=include_sessions,
        )
        return self._parse_response(response)

    def get_sessions(self, event_id: int) -> List[Dict[str, Any]]:
        """Get sessions for an event.

        Args:
            event_id: Event ID

        Returns:
            List of session dicts with keys like 'id', 'name', 'type', 'date', etc.
        """
        response = get_session_list.sync_detailed(id=event_id, client=self._client)
        result = self._parse_response(response)
        return result if isinstance(result, list) else []

    # -------------------------------------------------------------------------
    # Session endpoints
    # -------------------------------------------------------------------------

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session details by ID.

        Args:
            session_id: Session ID

        Returns:
            Session dict with keys like 'id', 'name', 'type', 'date', 'event', etc.
        """
        response = get_session.sync_detailed(id=session_id, client=self._client)
        return self._parse_response(response)

    def get_laps(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all lap times for a session.

        Args:
            session_id: Session ID

        Returns:
            List of lap dicts with keys like 'competitorId', 'lapNumber', 'lapTime', etc.
        """
        response = get_all_lap_times.sync_detailed(id=session_id, client=self._client)
        result = self._parse_response(response)
        # API may return {'rows': [...]} or a raw list
        if isinstance(result, dict):
            return result.get("rows", result.get("laps", []))
        return result if isinstance(result, list) else []

    def get_results(self, session_id: int) -> List[Dict[str, Any]]:
        """Get classification/results for a session.

        Args:
            session_id: Session ID

        Returns:
            List of result dicts with keys like 'position', 'competitor', 'time', etc.
        """
        response = get_classification.sync_detailed(id=session_id, client=self._client)
        result = self._parse_response(response)
        if isinstance(result, dict):
            return result.get("rows", result.get("classification", []))
        return result if isinstance(result, list) else []

    def get_announcements(self, session_id: int) -> List[Dict[str, Any]]:
        """Get announcements for a session.

        Args:
            session_id: Session ID

        Returns:
            List of announcement dicts with keys like 'text', 'timestamp', etc.
        """
        response = get_announcements.sync_detailed(id=session_id, client=self._client)
        result = self._parse_response(response)
        if isinstance(result, dict):
            return result.get("announcements", result.get("rows", []))
        return result if isinstance(result, list) else []

    # -------------------------------------------------------------------------
    # Utility endpoints
    # -------------------------------------------------------------------------

    def get_server_time(self) -> Optional[str]:
        """Get current server time.

        Returns:
            Server time string or None
        """
        result = time_api.sync(client=self._client)
        return result


# ---------------------------------------------------------------------------
# Legacy functions (kept for backward compatibility)
# ---------------------------------------------------------------------------

def make_client(base_url: str = "https://api2.mylaps.com", **kwargs) -> Client:
    """Create and return an `event_results_client.Client` instance.

    Any extra keyword args are forwarded to the generated `Client` constructor.

    Note: Consider using SpeedhiveClient instead for a friendlier API.
    """
    return Client(base_url=base_url, **kwargs)


def get_server_time(client: Optional[Client] = None):
    """Return the server time by calling the generated `system_time_controller`.

    If no `client` is provided, one is created with the default base_url.

    Note: Consider using SpeedhiveClient().get_server_time() instead.
    """
    client = client or make_client()
    return time_api.sync(client=client)


if __name__ == "__main__":
    # Quick demo
    client = SpeedhiveClient()

    print("Server time:", client.get_server_time())

    # Example: fetch first 5 events for org 30476
    print("\nEvents for org 30476:")
    events = client.get_events(org_id=30476, limit=5)
    for e in events:
        print(f"  - {e.get('id')}: {e.get('name')}")

