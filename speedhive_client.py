
# speedhive_client.py
# Dependencies: requests  (pip install requests)
#
# This client covers:
#   - Get organization by ID
#   - Iterate ALL org events via count/offset pagination (until exhausted)
#   - Recursively collect ALL sessions for an event (including nested groups/subGroups)
#   - Fetch announcements for a session
#   - Export ONLY "New Track Record" announcements to the exact JSON shape you requested
#   - (Optional) find organizations by name

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


class SpeedHiveError(Exception):
    """Domain-specific error for SpeedHive client operations."""


class SpeedHiveClient:
    """
    Thin, extendable client for MYLAPS Speedhive Event Results API.

    Current capabilities:
        - Get organization by ID
        - Iterate ALL org events
        - Get ALL sessions for an event (recursively)
        - Get announcements for a session
        - Export ONLY "New Track Record" announcements in requested JSON shape
        - Find organizations by name (best-effort)
    """

    BASE_URL = "https://eventresults-api.speedhive.com/api/v0.2.3/eventresults"

    # Known classes to help parse classAbbreviation if present
    KNOWN_CLASSES = {
        "FA", "FB", "FC", "FD", "FE", "FE2", "FF", "FM", "FS", "FX", "FV", "FST", "CFC", "ASR",
        "P1", "P2", "SPU",
        "F5", "F5-2-stroke", "F5-4-stroke",
    }

    # Lap time pattern: mm:ss.xxx (e.g., 1:06.111)
    LAPTIME_ANY_RE = re.compile(r"\b(\d+:\d{2}\.\d{3})\b")
    LAPTIME_PARENS_RE = re.compile(r"\(\s*(\d+:\d{2}\.\d{3})\s*\)")

    def __init__(
        self,
        sport_category: str = "Motorized",
        user_agent: str = "speedhive-client/0.3 (+https://github.com/ncrosty58/speedhive-tools)",
        timeout_seconds: int = 30,
        max_retries: int = 3,
        backoff_seconds: float = 1.5,
        session: Optional[requests.Session] = None,
        page_size: int = 25,  # Speedhive endpoints often page in 25s; we paginate until empty
    ) -> None:
        self.sport_category = sport_category
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.page_size = page_size
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": user_agent,
                "Referer": "https://speedhive.mylaps.com/",
            }
        )

    # ---------- low-level HTTP helper with basic retry ----------

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET helper with basic retry/backoff. Raises SpeedHiveError on failure."""
        url = f"{self.BASE_URL}{path}"
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout_seconds)
            except requests.RequestException as e:
                if attempt < self.max_retries:
                    time.sleep(self.backoff_seconds * attempt)
                    continue
                raise SpeedHiveError(f"Request failed: {url} :: {e}") from e

            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError as e:
                    raise SpeedHiveError(f"Invalid JSON at {url}: {e}") from e

            # Retry typical transient statuses
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                time.sleep(self.backoff_seconds * attempt)
                continue

            # Non-retryable error
            raise SpeedHiveError(
                f"GET {url} failed with status {resp.status_code} :: {resp.text[:300]}"
            )

    # ---------- organizations ----------

    def get_organization(self, organization_id: int) -> Dict[str, Any]:
        """
        GET /eventresults/organizations/{id}
        """
        return self._get(f"/organizations/{organization_id}")

    # Alias to match earlier runner call you had
    def get_organization_by_id(self, organization_id: int) -> Dict[str, Any]:
        return self.get_organization(organization_id)

    def iter_organization_events(
        self, organization_id: int, start_offset: int = 0
    ) -> Iterable[Dict[str, Any]]:
        """
        Iterate ALL events for an organization using count/offset until no more results.

        GET /eventresults/organizations/{id}/events?count=&offset=&sportCategory=
        """
        offset = start_offset
        page_size = self.page_size
        while True:
            payload = self._get(
                f"/organizations/{organization_id}/events",
                params={"count": page_size, "offset": offset, "sportCategory": self.sport_category},
            )
            # Expect an array (per Swagger); allow wrapped shapes just in case
            if isinstance(payload, list):
                events = payload
            else:
                events = payload.get("events") or payload.get("data") or []

            if not events:
                break

            for ev in events:
                yield ev

            # advance pagination
            offset += page_size

            # If server returned fewer than our page_size, we reached the end
            if len(events) < page_size:
                break

    # ---------- events & sessions ----------

    def get_event(self, event_id: int) -> Dict[str, Any]:
        """
        GET /eventresults/events/{eventId}?sessions=true
        Return the raw EventDto for session grouping traversal.
        """
        return self._get(f"/events/{event_id}", params={"sessions": True})

    def get_event_sessions(self, event_id: int) -> List[Dict[str, Any]]:
        """
        Return ALL sessions for the given event, including sessions nested in groups/subGroups.

        EventDto.sessions is a SessionGroupingDto with:
          - 'sessions' (list)
          - 'groups' (list of SessionGroupDto, each with 'sessions' and 'subGroups')
        """
        event = self.get_event(event_id)
        grouping = event.get("sessions") or {}

        all_sessions: List[Dict[str, Any]] = []

        # Collect top-level sessions
        top_sessions = grouping.get("sessions")
        if isinstance(top_sessions, list):
            all_sessions.extend(top_sessions)

        # Recursively collect from groups/subGroups
        def walk_groups(groups: List[Dict[str, Any]]):
            for g in groups or []:
                g_sessions = g.get("sessions")
                if isinstance(g_sessions, list):
                    all_sessions.extend(g_sessions)
                sub = g.get("subGroups")
                if isinstance(sub, list) and sub:
                    walk_groups(sub)

        g = grouping.get("groups")
        if isinstance(g, list) and g:
            walk_groups(g)

        return all_sessions

    def get_session_announcements(self, session_id: int) -> List[Dict[str, Any]]:
        """
        GET /eventresults/sessions/{sessionId}/announcements
        Returns RunAnnouncementsDto with 'rows' [{timestamp, text}, ...]
        """
        ra = self._get(f"/sessions/{session_id}/announcements")
        rows = ra.get("rows") or []
        return [{"timestamp": r.get("timestamp"), "text": r.get("text")} for r in rows]

    # ---------- discovery by name (best-effort) ----------

    def find_organizations_by_name(
        self, name: str, max_events_to_scan: int = 2000
    ) -> List[Tuple[int, str]]:
        """
        Try deprecated free search; fall back to scanning public events.
        Returns list of (organization_id, organization_name).
        """
        discovered: Dict[int, str] = {}

        # Attempt free search (visible in Swagger but documented as deprecated)
        try:
            sr = self._get(
                "/search/freesearch",
                params={
                    "searchTerm": name,
                    "sportCategory": self.sport_category,
                    "count": 25,
                    "offset": 0,
                    "filter": "Events",
                },
            )
            for key in ("events", "results", "items"):
                for ev in sr.get(key, []) or []:
                    org = ev.get("organization") or {}
                    org_id = org.get("id")
                    org_name = org.get("name")
                    if org_id and org_name and name.lower() in org_name.lower():
                        discovered[org_id] = org_name
        except SpeedHiveError:
            pass

        # Fallback: scan public events and collect organizations matching the name
        scanned = 0
        offset = 0
        page_size = self.page_size
        while scanned < max_events_to_scan:
            events_page = self._get(
                "/events",
                params={
                    "sport": "All",
                    "sportCategory": self.sport_category,
                    "count": page_size,
                    "offset": offset,
                },
            )
            if not isinstance(events_page, list) or not events_page:
                break

            for ev in events_page:
                scanned += 1
                org = (ev or {}).get("organization") or {}
                org_id = org.get("id")
                org_name = org.get("name") or ""
                if org_id and org_name and name.lower() in org_name.lower():
                    discovered[org_id] = org_name

            if len(events_page) < page_size:
                break
            offset += page_size
            if scanned >= max_events_to_scan:
                break

        return sorted(discovered.items(), key=lambda t: t[1].lower())

    # ---------- parsing helpers for "New Track Record" ----------

    @staticmethod
    def _normalize_whitespace(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "")).strip()

    @classmethod
    def _clean_tail(cls, s: str) -> str:
        """Trim stray punctuation or trailing separators."""
        return s.strip().rstrip(" .;:!|-")

    @classmethod
    def _parse_record_announcement(cls, text: str, timestamp: Optional[str]) -> Optional[Dict[str, str]]:
        """
        Parse a single announcement row (text must contain 'New Track Record') into:
            { "classAbbreviation", "lapTime", "driverName", "marque", "date" }

        Expected canonical shape:
            "New Track Record (<lap>) for <class> by <driver> in <marque>"

        Strategy:
            - Require 'New Track Record' (case-insensitive)
            - Extract lap time primarily from parentheses; fallback to generic pattern
            - From the tail (text after lap time's closing paren), use regex windows to capture
              'for <class>', 'by <driver>', 'in <marque>'
            - date from timestamp (YYYY-MM-DD)
        """
        if not text or "new track record" not in text.lower():
            return None

        txt = cls._normalize_whitespace(text)

        # Lap time: prefer parentheses, fallback to any
        lap_paren = cls.LAPTIME_PARENS_RE.search(txt)
        lap_any = cls.LAPTIME_ANY_RE.search(txt)
        lap_match = lap_paren or lap_any
        lap_time = lap_match.group(1) if lap_match else None
        if not lap_time:
            return None  # only emit records that include a lap time

        # Date (YYYY-MM-DD from timestamp; works for ISO with or without Z)
        date_str = ""
        if timestamp:
            m = re.match(r"(\d{4}-\d{2}-\d{2})", timestamp)
            if m:
                date_str = m.group(1)

        # Tail: start scanning right after the lap time we found
        tail = txt[lap_match.end():].strip()

        # Extract classAbbreviation
        m_for = re.search(r"(?i)\bfor\s+(.+?)(?=\s+by\b|\s*$)", tail)
        class_abbr = cls._clean_tail(m_for.group(1)) if m_for else ""

        # Extract driverName
        m_by = re.search(r"(?i)\bby\s+(.+?)(?=\s+in\b|\s*$)", tail)
        driver_name = cls._clean_tail(m_by.group(1)) if m_by else ""

        # Extract marque
        m_in = re.search(r"(?i)\bin\s+(.+)$", tail)
        marque = cls._clean_tail(m_in.group(1)) if m_in else ""

        # Sanity: avoid capturing "(" as driver name (symptom you reported)
        if driver_name == "(":
            driver_name = ""

        # Optional: validate class token against known set; if it's obviously not a class, keep anyway
        # (Some tracks use custom labels; better to return what was written.)
        return {
            "classAbbreviation": class_abbr,
            "lapTime": lap_time,
            "driverName": driver_name,
            "marque": marque,
            "date": date_str,
        }

    # ---------- export ----------

    def export_all_track_records_for_organization(
        self,
        organization_id: int,
        output_json_path: str,
    ) -> Dict[str, Any]:
        """
        Traverse ALL org events -> ALL sessions -> announcements and write a single JSON file.

        Output JSON EXACTLY:
            { "records": [ {classAbbreviation, lapTime, driverName, marque, date}, ... ] }
        """
        records_out: List[Dict[str, str]] = []

        for ev in self.iter_organization_events(organization_id):
            event_id = ev.get("id")
            if not event_id:
                continue

            sessions = self.get_event_sessions(event_id)
            for sess in sessions:
                session_id = sess.get("id")
                if not session_id:
                    continue

                announcements = self.get_session_announcements(session_id)
                for ann in announcements:
                    parsed = self._parse_record_announcement(
                        ann.get("text") or "", ann.get("timestamp")
                    )
                    if parsed:
                        records_out.append(parsed)

        # Optional: sort results by date (oldest first)
        def _date_key(rec: Dict[str, str]) -> str:
            return rec.get("date") or ""

        records_out.sort(key=_date_key)

        output = {"records": records_out}

        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        return output

    def export_all_track_records_for_organization_name(
        self, organization_name: str, output_json_path: str
    ) -> Dict[str, Any]:
        matches = self.find_organizations_by_name(organization_name)
        if not matches:
            raise SpeedHiveError(f"No organizations found by name: {organization_name}")
        org_id, _ = matches[0]
        return self.export_all_track_records_for_organization(org_id, output_json_path)
