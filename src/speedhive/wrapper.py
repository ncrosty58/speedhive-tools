"""User‑friendly wrapper around the low‑level client."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterator, List, Optional

from attrs import define, field

from speedhive.client import Client, AuthenticatedClient
from speedhive.generated.api.system_time_controller import get_time as time_api
from speedhive.generated.api.organization_controller import get_event_list, get_organization, get_championship_list
from speedhive.generated.api.event_controller import get_event, get_session_list
from speedhive.generated.api.session_controller import (
    get_all_lap_times,
    get_classification,
    get_announcements,
    get_session,
    get_lap_chart,
)
from speedhive.generated.api.championship_controller import get_championship
from speedhive.generated.models.time import Time as TimeModel


@define
class SpeedhiveClient:
    client: Client | AuthenticatedClient = field()

    @staticmethod
    def _parse_response(response) -> Any:
        if not response.content:
            return None
        return json.loads(response.content)

    # Organization
    def get_organization(self, org_id: int) -> Optional[Dict[str, Any]]:
        response = get_organization.sync_detailed(id=org_id, client=self.client)
        return self._parse_response(response)

    def get_events(self, org_id: int, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        kwargs = {"id": org_id, "client": self.client, "offset": offset}
        if limit is not None:
            kwargs["count"] = limit
        response = get_event_list.sync_detailed(**kwargs)
        result = self._parse_response(response)
        return result if isinstance(result, list) else []

    def iter_events(self, org_id: int, page_size: int = 100) -> Iterator[Dict[str, Any]]:
        offset = 0
        while True:
            events = self.get_events(org_id=org_id, limit=page_size, offset=offset)
            if not events:
                break
            yield from events
            if len(events) < page_size:
                break
            offset += page_size

    # Event
    def get_event(self, event_id: int, include_sessions: bool = False) -> Optional[Dict[str, Any]]:
        response = get_event.sync_detailed(
            id=event_id, client=self.client, sessions=include_sessions
        )
        return self._parse_response(response)

    def get_sessions(self, event_id: int) -> List[Dict[str, Any]]:
        response = get_session_list.sync_detailed(id=event_id, client=self.client)
        result = self._parse_response(response)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            sessions = []
            for key in ("sessions", "groups"):
                if isinstance(result.get(key), list):
                    sessions.extend(result[key])
            if isinstance(result.get("groups"), list):
                for g in result["groups"]:
                    if isinstance(g.get("sessions"), list):
                        sessions.extend(g["sessions"])
            return sessions
        return []

    # Session
    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        response = get_session.sync_detailed(id=session_id, client=self.client)
        return self._parse_response(response)

    def get_laps(self, session_id: int, flatten: bool = True) -> List[Dict[str, Any]]:
        response = get_all_lap_times.sync_detailed(id=session_id, client=self.client)
        result = self._parse_response(response)
        if isinstance(result, dict):
            rows = result.get("rows", result.get("laps", []))
            if not flatten:
                return rows
            result = rows
        if not isinstance(result, list):
            return []
        flat = []
        for item in result:
            if isinstance(item, dict) and "laps" in item:
                for lap in item["laps"]:
                    flat.append({
                        "competitorId": item.get("competitorId") or item.get("id"),
                        "position": item.get("position"),
                        "lapNumber": lap.get("lap") or lap.get("lapNumber"),
                        "lapTime": lap.get("lapTime") or lap.get("lap_time"),
                        "speed": lap.get("speed"),
                        "inPit": lap.get("inPit"),
                        **{k: v for k, v in lap.items()
                           if k not in ("lap", "lapNumber", "lapTime", "lap_time", "speed", "inPit")}
                    })
            else:
                flat.append(item)
        return flat

    def get_results(self, session_id: int) -> List[Dict[str, Any]]:
        response = get_classification.sync_detailed(id=session_id, client=self.client)
        result = self._parse_response(response)
        if isinstance(result, dict):
            return result.get("rows", result.get("classification", []))
        return result if isinstance(result, list) else []

    def get_announcements(self, session_id: int) -> List[Dict[str, Any]]:
        response = get_announcements.sync_detailed(id=session_id, client=self.client)
        result = self._parse_response(response)
        if isinstance(result, dict):
            return result.get("announcements", result.get("rows", []))
        return result if isinstance(result, list) else []

    def get_lap_chart(self, session_id: int) -> List[Dict[str, Any]]:
        response = get_lap_chart.sync_detailed(id=session_id, client=self.client)
        result = self._parse_response(response)
        if isinstance(result, dict):
            return result.get("rows", result.get("chart", []))
        return result if isinstance(result, list) else []

    # Championships
    def get_championships(self, org_id: int) -> List[Dict[str, Any]]:
        response = get_championship_list.sync_detailed(id=org_id, client=self.client)
        result = self._parse_response(response)
        return result if isinstance(result, list) else []

    def get_championship(self, championship_id: int) -> Optional[Dict[str, Any]]:
        response = get_championship.sync_detailed(id=championship_id, client=self.client)
        return self._parse_response(response)

    # Utility
    def get_server_time(self) -> Optional[TimeModel]:
        return time_api.sync(client=self.client)

    # Track records – uses the parser from processing
    def get_track_records(
        self, org_id: int, classification: Optional[str] = None, limit_events: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        from speedhive.processing.lap_analysis import parse_track_record_text
        records = []
        event_iter = self.iter_events(org_id=org_id)
        if limit_events is not None:
            from itertools import islice
            event_iter = islice(event_iter, limit_events)
        for event in event_iter:
            eid = event.get("id")
            ename = event.get("name")
            if not eid:
                continue
            try:
                sessions = self.get_sessions(event_id=eid)
            except Exception:
                continue
            for session in sessions:
                sid = session.get("id")
                sname = session.get("name")
                if not sid:
                    continue
                try:
                    announcements = self.get_announcements(session_id=sid)
                except Exception:
                    continue
                for ann in announcements:
                    text = ann.get("text") or ann.get("message") or ""
                    ts = ann.get("timestamp") or ann.get("time")
                    parsed = parse_track_record_text(text)
                    if not parsed:
                        continue
                    class_name = parsed.get("classification")
                    if classification and class_name.upper() != classification.upper():
                        continue
                    lap_seconds = parsed.get("lap_time_seconds")
                    records.append({
                        "event_id": eid, "event_name": ename,
                        "session_id": sid, "session_name": sname,
                        "classification": class_name,
                        "lap_time": parsed.get("lap_time"),
                        "lap_time_seconds": lap_seconds,
                        "driver": parsed.get("driver"),
                        "marque": parsed.get("marque"),
                        "timestamp": ts, "text": text,
                    })
        records.sort(key=lambda r: (r["classification"], r["lap_time_seconds"] or float('inf')))
        return records

    def get_fastest_track_record(
        self, org_id: int, classification: str, limit_events: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        records = self.get_track_records(org_id, classification, limit_events)
        return records[0] if records else None

    def iter_track_records_by_event(
        self, org_id: int, classification: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        pattern = re.compile(
            r"New (?:Track|Class) Record\s*\(([0-9:.]+)\)\s*for\s+([^\s]+)\s+by\s+(.+?)\.?$",
            re.IGNORECASE
        )
        for event in self.iter_events(org_id=org_id):
            eid = event.get("id")
            ename = event.get("name")
            if not eid:
                continue
            try:
                sessions = self.get_sessions(event_id=eid)
            except Exception:
                continue
            for session in sessions:
                sid = session.get("id")
                sname = session.get("name")
                if not sid:
                    continue
                try:
                    announcements = self.get_announcements(session_id=sid)
                except Exception:
                    continue
                for ann in announcements:
                    text = ann.get("text") or ann.get("message") or ""
                    ts = ann.get("timestamp") or ann.get("time")
                    match = pattern.search(text)
                    if not match:
                        continue
                    lap_time_str = match.group(1)
                    class_name = match.group(2)
                    driver_block = match.group(3).strip()
                    low = text.lower()
                    if any(x in low for x in ("to be confirmed", "not a track record", "not a class record")):
                        continue
                    marque = None
                    m = re.search(r"^(.+?)\s+in\s+(.+)$", driver_block, re.IGNORECASE)
                    if m:
                        driver = m.group(1).strip()
                        marque = m.group(2).strip().rstrip('.')
                    else:
                        driver = driver_block
                    driver = re.sub(r"^\s*\[\s*\d+\s*\]\s*", "", driver)
                    if classification and class_name.upper() != classification.upper():
                        continue
                    lap_seconds = self._parse_lap_time(lap_time_str)
                    yield {
                        "event_id": eid, "event_name": ename,
                        "session_id": sid, "session_name": sname,
                        "classification": class_name,
                        "lap_time": lap_time_str, "lap_time_seconds": lap_seconds,
                        "driver": driver, "marque": marque,
                        "timestamp": ts, "text": text,
                    }

    @staticmethod
    def _parse_lap_time(lap_time_str: str) -> Optional[float]:
        try:
            parts = lap_time_str.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            return float(lap_time_str)
        except (ValueError, IndexError):
            return None
