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
from typing import Any, Dict, Iterator, List, Optional, cast

from event_results_client import Client, AuthenticatedClient
from event_results_client.api.system_time_controller import get_time as time_api
from event_results_client.models.time import Time as TimeModel
from event_results_client.api.organization_controller import get_event_list, get_organization, get_championship_list
from event_results_client.api.event_controller import get_event, get_session_list
from event_results_client.api.session_controller import (
    get_all_lap_times,
    get_classification,
    get_announcements,
    get_session,
    get_lap_chart,
)
from event_results_client.api.championship_controller import get_championship


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
    _client: Client | AuthenticatedClient = field(init=False, repr=False)

    def __post_init__(self):
        if self.token:
            self._client = AuthenticatedClient(
                base_url=self.base_url,
                token=self.token,
                timeout=cast(Any, self.timeout),
            )
        else:
            self._client = Client(
                base_url=self.base_url,
                timeout=cast(Any, self.timeout),
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

        # Handle various response formats
        if isinstance(result, list):
            return result

        if isinstance(result, dict):
            sessions = []
            # Direct sessions array
            if isinstance(result.get("sessions"), list):
                sessions.extend(result["sessions"])
            # Sessions nested under groups
            for group in result.get("groups", []):
                if isinstance(group.get("sessions"), list):
                    sessions.extend(group["sessions"])
            return sessions

        return []

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

    def get_laps(self, session_id: int, flatten: bool = True) -> List[Dict[str, Any]]:
        """Get all lap times for a session.

        Args:
            session_id: Session ID
            flatten: If True, flatten laps from all competitors into a single list
                     with competitor info included. If False, return raw response.

        Returns:
            List of lap dicts with keys like 'competitorId', 'lapNumber', 'lapTime', etc.
        """
        response = get_all_lap_times.sync_detailed(id=session_id, client=self._client)
        result = self._parse_response(response)

        # Handle various response formats
        if isinstance(result, dict):
            rows = result.get("rows", result.get("laps", []))
            if not flatten:
                return rows
            result = rows

        if not isinstance(result, list):
            return []

        # Check if this is already flattened or needs flattening
        # Format 1: List of competitors with nested laps
        # Format 2: Already flat list of lap records
        if result and isinstance(result[0], dict):
            if "laps" in result[0]:
                # Format 1: Need to flatten - each item is a competitor with laps array
                if not flatten:
                    return result
                flat = []
                for competitor in result:
                    comp_id = competitor.get("competitorId") or competitor.get("id")
                    position = competitor.get("position")
                    for lap in competitor.get("laps", []):
                        flat.append({
                            "competitorId": comp_id,
                            "position": position,
                            "lapNumber": lap.get("lap") or lap.get("lapNumber"),
                            "lapTime": lap.get("lapTime") or lap.get("lap_time"),
                            "speed": lap.get("speed"),
                            "inPit": lap.get("inPit"),
                            **{k: v for k, v in lap.items() if k not in ("lap", "lapNumber", "lapTime", "lap_time", "speed", "inPit")}
                        })
                return flat
            else:
                # Format 2: Already flat
                return result

        return result

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

    def get_lap_chart(self, session_id: int) -> List[Dict[str, Any]]:
        """Get lap chart data for a session (position changes per lap).

        This is useful for visualizing race progress and position changes.

        Args:
            session_id: Session ID

        Returns:
            List of lap chart entries showing position per lap for each competitor.
        """
        response = get_lap_chart.sync_detailed(id=session_id, client=self._client)
        result = self._parse_response(response)
        if isinstance(result, dict):
            return result.get("rows", result.get("chart", []))
        return result if isinstance(result, list) else []

    # -------------------------------------------------------------------------
    # Championship endpoints
    # -------------------------------------------------------------------------

    def get_championships(self, org_id: int) -> List[Dict[str, Any]]:
        """Get championships for an organization.

        Args:
            org_id: Organization ID

        Returns:
            List of championship dicts with keys like 'id', 'name', 'year', etc.
        """
        response = get_championship_list.sync_detailed(id=org_id, client=self._client)
        result = self._parse_response(response)
        return result if isinstance(result, list) else []

    def get_championship(self, championship_id: int) -> Optional[Dict[str, Any]]:
        """Get championship details and standings.

        Args:
            championship_id: Championship ID

        Returns:
            Championship dict with standings, events, and point allocations.
        """
        response = get_championship.sync_detailed(id=championship_id, client=self._client)
        return self._parse_response(response)

    # -------------------------------------------------------------------------
    # Utility endpoints
    # -------------------------------------------------------------------------

    def get_server_time(self) -> Optional[TimeModel]:
        """Get current server time.

        Returns:
            Server time model or None
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

