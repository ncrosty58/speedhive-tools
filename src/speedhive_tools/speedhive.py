
import json
from typing import Any, Dict, List
from .config import Settings
from .client import get_api_client

class Speedhive:
    """Ergonomic façade for common Speedhive operations."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.client = get_api_client(self.settings)

    # --- Events list ---
    def events(
        self,
        *,
        count: int | None = None,
        offset: int | None = None,
        sport: str | None = None,
        sport_category: str | None = None,
        country: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> List[Dict[str, Any]]:
        from event_results_client.api.event_controller import get_event_list_1

        resp = get_event_list_1.sync_detailed(
            client=self.client,
            count=count,
            offset=offset,
            sport=sport,
            sport_category=sport_category,
            country=country,
            start_date=start_date,
            end_date=end_date,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"API error {resp.status_code}: {resp.content!r}")

        if resp.parsed is not None:
            # If parsed is a list of typed models, convert to dict rows
            if isinstance(resp.parsed, list):
                return [
                    getattr(ev, "model_dump", getattr(ev, "to_dict", lambda: ev))()
                    for ev in resp.parsed
                ]
            return [resp.parsed.model_dump()] if hasattr(resp.parsed, "model_dump") else [resp.parsed]

        # Fallback to raw JSON when the generator can’t type the payload
        return json.loads(resp.content.decode("utf-8"))

    # --- Single session by id (usually well-typed) ---
    def session(self, session_id: int) -> Dict[str, Any]:
        from event_results_client.api.session_controller import get_session

        resp = get_session.sync_detailed(client=self.client, id=session_id)
        if resp.status_code != 200:
            raise RuntimeError(f"API error {resp.status_code}: {resp.content!r}")

        if resp.parsed is not None:
            return resp.parsed.model_dump() if hasattr(resp.parsed, "model_dump") else resp.parsed
        return json.loads(resp.content.decode("utf-8"))

    # --- Sessions for an event (if you want this, useful next) ---
    def event_sessions(self, event_id: int) -> Dict[str, Any] | List[Dict[str, Any]]:
        from event_results_client.api.event_controller import get_session_list

        resp = get_session_list.sync_detailed(client=self.client, id=event_id)
        if resp.status_code != 200:
            raise RuntimeError(f"API error {resp.status_code}: {resp.content!r}")

        if resp.parsed is not None:
            # This endpoint may return a complex object (EventSessionsAndGroups)
            return resp.parsed.model_dump() if hasattr(resp.parsed, "model_dump") else resp.parsed

        return json.loads(resp.content.decode("utf-8"))
    
    def session_classification(self, session_id: int):
        """Return classification details for a session."""
        from event_results_client.api.session_controller import get_classification

        resp = get_classification.sync_detailed(client=self.client, id=session_id)
        if resp.status_code != 200:
            raise RuntimeError(f"API error {resp.status_code}: {resp.content!r}")

        if resp.parsed is not None:
            return resp.parsed.model_dump() if hasattr(resp.parsed, "model_dump") else resp.parsed
        return json.loads(resp.content.decode("utf-8"))

    def session_lapchart(self, session_id: int):
        """Return lap chart (position per lap) for a session."""
        from event_results_client.api.session_controller import get_lap_chart

        resp = get_lap_chart.sync_detailed(client=self.client, id=session_id)
        if resp.status_code != 200:
            raise RuntimeError(f"API error {resp.status_code}: {resp.content!r}")

        if resp.parsed is not None:
            return resp.parsed.model_dump() if hasattr(resp.parsed, "model_dump") else resp.parsed
        return json.loads(resp.content.decode("utf-8"))

