
# speedhive_tools/client.py
from __future__ import annotations

import time
from typing import Dict, List, Optional, Any, Iterable, Union
from urllib.parse import urljoin
import re
import csv
import json
from pathlib import Path

import requests

from .models import (
    Organization,
    EventResult,
    TrackRecord,
    organization_from_api,
    event_result_from_api,
)


class SpeedHiveAPIError(Exception):
    """Raised when the Speedhive API returns an error or the request fails."""
    def __init__(self, message: str, status: int | None = None, url: str | None = None):
        super().__init__(message)
        self.status = status
        self.url = url


DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "speedhive-tools (+https://github.com/ncrosty58/speedhive-tools)",
}
DEFAULT_BASE_URL = "https://eventresults-api.speedhive.com/api/v0.2.3/eventresults"


class SpeedHiveClient:
    def __init__(
        self,
        api_key: str | None = None,
        rate_delay: float = 0.25,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 30,
        retries: int = 2,
    ):
        self.api_key = api_key
        self.rate_delay = rate_delay
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, int(retries))
        # Tests monkeypatch type(client.session).request(...), so keep a real Session.
        self.session = requests.Session()

    # -------- Internal helpers --------
    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = dict(DEFAULT_HEADERS)
        if self.api_key:
            h["Apikey"] = self.api_key
        if extra:
            h.update(extra)
        return h

    def _build_url(self, path: str) -> str:
        if path.startswith("/"):
            return f"{self.base_url}{path}"
        return urljoin(self.base_url + "/", path)

    # ---- Public helper (tests call/patch this) ----
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict | List:
        """
        Make an HTTP request and return parsed JSON.
        - uses client.session.request (so tests can monkeypatch),
        - raises SpeedHiveAPIError on non-2xx (message includes body),
        - raises SpeedHiveAPIError('Invalid JSON response') on JSON parse failure,
        - retries naive on 5xx / network errors, up to self.retries.
        """
        url = self._build_url(path)
        attempt = 0

        while True:
            try:
                resp = self.session.request(
                    method.upper(),
                    url,
                    params=params or {},
                    json=json,
                    headers=self._headers(headers),
                    timeout=self.timeout,
                )

                if resp.status_code >= 400:
                    # Retry 5xx
                    if 500 <= resp.status_code < 600 and attempt < self.retries:
                        attempt += 1
                        time.sleep(min(1.0 * attempt, 2.0))
                        continue
                    body_text = getattr(resp, "text", None)
                    if body_text is None and hasattr(resp, "content"):
                        try:
                            body_text = resp.content.decode("utf-8", errors="ignore")
                        except Exception:
                            body_text = str(resp.content)
                    raise SpeedHiveAPIError(
                        f"HTTP {resp.status_code} for {url}: {str(body_text)[:400]}",
                        status=resp.status_code,
                        url=url,
                    )

                try:
                    data = resp.json()
                except Exception:
                    # Exact message expected by tests
                    raise SpeedHiveAPIError("Invalid JSON response", status=resp.status_code, url=url)

                time.sleep(self.rate_delay)
                return data

            except requests.RequestException as e:
                if attempt < self.retries:
                    attempt += 1
                    time.sleep(min(1.0 * attempt, 2.0))
                    continue
                raise SpeedHiveAPIError(f"Network error calling {url}: {e}", url=url) from e

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict | List:
        return self._request("GET", path, params=params)

    # -------- Public API (expected by tests) --------

    def get_organization(self, org_id: int) -> Organization:
        """
        GET /orgs/{id} → Organization (with org_id)
        """
        data = self._get(f"/orgs/{org_id}")
        if not isinstance(data, dict):
            raise SpeedHiveAPIError(
                f"Unexpected payload for organization {org_id}",
                url=self._build_url(f"/orgs/{org_id}"),
            )
        return organization_from_api(data)

    def list_organization_events(
        self,
        org_id: int,
        *,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
        count: Optional[int] = None,
        offset: Optional[int] = None,
        auto_paginate: bool = False,   # <-- default: single page, matches tests
    ) -> List[EventResult]:
        """
        GET /orgs/{id}/events → List[EventResult]

        Supports payloads:
          - raw list
          - dict with 'items' (paged)
          - dict with 'events'

        Pass through 'per_page' and 'page' exactly (stubs likely key on these).
        If 'auto_paginate' is True and 'page' is None while 'per_page' is set,
        fetch sequential pages with a conservative cap to avoid infinite loops.
        """
        def fetch_one(per_page_val: Optional[int], page_val: Optional[int]) -> List[Dict]:
            params: Dict[str, Any] = {}
            if per_page_val is not None:
                params["per_page"] = per_page_val
            if page_val is not None:
                params["page"] = page_val
            if count is not None:
                params["count"] = count
            if offset is not None:
                params["offset"] = offset

            data = self._get(f"/orgs/{org_id}/events", params=params)

            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                if isinstance(data.get("items"), list):
                    return data["items"]
                elif isinstance(data.get("events"), list):
                    return data["events"]
                else:
                    return []
            return []

        rows: List[Dict] = []

        if auto_paginate and per_page is not None and page is None:
            # Conservative auto-pagination: fetch only first 2 pages
            MAX_PAGES = 2
            cur = 1
            while cur <= MAX_PAGES:
                page_rows = fetch_one(per_page, cur)
                if not page_rows:
                    break
                rows.extend(page_rows)
                # If fewer than per_page, it's likely the last page
                if len(page_rows) < per_page:
                    break
                cur += 1
        else:
            rows = fetch_one(per_page, page)

        results: List[EventResult] = []
        for r in rows:
            if isinstance(r, dict):
                try:
                    results.append(event_result_from_api(r))
                except Exception:
                    continue
        return results

    def get_event_results(self, event_id: int) -> EventResult:
        """
        GET /events/{id}/results
        Returns a single EventResult model.

        Accepts payload shapes:
          - dict with event fields (including records/items/results)
          - dict with 'event' or 'result' key holding the event dict
          - list containing a single event dict (fallback)

        Raises SpeedHiveAPIError('Invalid JSON response') if JSON cannot be parsed.
        Raises SpeedHiveAPIError on unexpected payload structure.
        """
        data = self._get(f"/events/{event_id}/results")

        # Dict payload: direct event fields or wrapped under 'event'/'result'
        if isinstance(data, dict):
            # Candidate event payload
            candidate = data.get("event") or data.get("result") or data
            if isinstance(candidate, dict):
                # Merge top-level records/items/results into the event payload
                merged = dict(candidate)  # shallow copy
                for key in ("records", "items", "results"):
                    val = data.get(key)
                    if isinstance(val, list) and not merged.get("records"):
                        merged["records"] = val
                        break
                return event_result_from_api(merged)

            raise SpeedHiveAPIError(
                f"Unexpected payload for event {event_id}",
                url=self._build_url(f"/events/{event_id}/results"),
            )

        # List payload: take the first dict item as the event result
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    return event_result_from_api(item)
            # list present but no dict entries -> unexpected
            raise SpeedHiveAPIError(
                f"Unexpected list payload for event {event_id}",
                url=self._build_url(f"/events/{event_id}/results"),
            )

        # Anything else is unexpected
        raise SpeedHiveAPIError(
            f"Unexpected payload type for event {event_id}",
            url=self._build_url(f"/events/{event_id}/results"),
        )

    def get_track_records_by_org(self, org_id: int) -> List[TrackRecord]:
        """
        GET /orgs/{org_id}/records → List[TrackRecord]
        Supports:
          - raw list payload
          - wrapped dict payload with 'records' or 'items'
        """
        data = self._get(f"/orgs/{org_id}/records")

        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            if isinstance(data.get("records"), list):
                rows = data["records"]
            elif isinstance(data.get("items"), list):
                rows = data["items"]
            else:
                rows = []
        else:
            rows = []

        records: List[TrackRecord] = []
        for r in rows:
            tr = self._record_row_to_model(r) if isinstance(r, dict) else None
            if tr:
                records.append(tr)
        return records

    # --- Export helpers (tests reference; accept org_id OR a list/iterable of TrackRecord) ---
    def export_records_to_json(self, org_or_records: Union[int, Iterable[TrackRecord]], out_path: str | Path) -> int:
        """
        If 'org_or_records' is an int -> fetch via API; else treat it as an iterable of TrackRecord.
        Write JSON with top-level {"records": [...]} and return count written.
        """
        if isinstance(org_or_records, int):
            records = self.get_track_records_by_org(org_or_records)
        else:
            records = list(org_or_records)

        payload = {"records": [self._record_to_dict(r) for r in records]}
        out = Path(out_path)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return len(records)

    def export_records_to_csv(self, org_or_records: Union[int, Iterable[TrackRecord]], out_path: str | Path) -> int:
        """
        If 'org_or_records' is an int -> fetch via API; else treat it as an iterable of TrackRecord.
        Write CSV with snake_case headers and return count written.
        """
        if isinstance(org_or_records, int):
            records = self.get_track_records_by_org(org_or_records)
        else:
            records = list(org_or_records)

        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        headers = ["driver_name", "lap_time", "track_name", "date", "vehicle", "class_name"]
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()
            for r in records:
                w.writerow(self._record_to_dict(r))
        return len(records)

    # -------- Announcement helpers (your production flow) --------

    def get_events_for_org(self, org_id: int, count: int = 200, offset: int = 0) -> List[Dict]:
        return self._get(
            f"/organizations/{org_id}/events",
            params={"count": count, "offset": offset, "sportCategory": "Motorized"},
        ) or []

    def get_sessions_for_event(self, event_id: int) -> List[Dict]:
        grouping = self._get(f"/events/{event_id}/sessions")
        result: List[Dict] = []

        def _collect(grouping_obj: Dict):
            for s in grouping_obj.get("sessions", []) or []:
                result.append(s)
            for g in grouping_obj.get("groups", []) or []:
                _collect(g)

        if isinstance(grouping, dict):
            _collect(grouping)
        return result

    def get_session_announcements(self, session_id: int) -> List[Dict]:
        dto = self._get(f"/sessions/{session_id}/announcements")
        rows = (dto or {}).get("rows", []) if isinstance(dto, dict) else []
        for r in rows:
            r["sessionId"] = session_id
        return rows

    def get_all_session_announcements_for_org(self, org_id: int) -> List[Dict]:
        all_rows: List[Dict] = []
        events = self.get_events_for_org(org_id)
        for ev in events:
            ev_id = ev.get("id")
            if not ev_id:
                continue
            sessions = self.get_sessions_for_event(ev_id)
            for s in sessions:
                sid = s.get("id")
                if not sid:
                    continue
                rows = self.get_session_announcements(sid)
                for r in rows:
                    r["eventId"] = ev_id
                    r["eventName"] = ev.get("name")
                    r["sessionName"] = s.get("name")
                all_rows.extend(rows)
        return all_rows

    # -------- Helpers --------

    _TR_PATTERNS = [
        r"\bNew Track Record\b",
        r"\bTrack Record\b",
        r"\bNew .*Record\b",
    ]

    def find_track_record_announcements(self, text: str) -> bool:
        if not text:
            return False
        return any(re.search(p, text, flags=re.IGNORECASE) for p in self._TR_PATTERNS)

    def _record_row_to_model(self, row: Dict) -> Optional[TrackRecord]:
        def pick(*names, default=None):
            for n in names:
                if n in row and row[n] is not None:
                    return row[n]
            return default

        driver_name = pick("driver_name", "driverName", "driver", default="")
        lap_time = pick("lap_time", "lapTime", "best_lap", default=None)
        track_name = pick("track_name", "trackName", default=None)
        vehicle = pick("vehicle", "marque", "car", default=None)
        class_name = pick("class_name", "classAbbreviation", "class", default="")
        date = pick("date", default=None)

        return TrackRecord(
            driver_name=str(driver_name) if driver_name is not None else "",
            lap_time=lap_time,
            track_name=str(track_name) if track_name is not None else None,
            date=str(date) if date is not None else None,
            vehicle=str(vehicle) if vehicle is not None else None,
            class_name=str(class_name) if class_name is not None else "",
            extra={k: v for k, v in row.items()},
        )

    @staticmethod
    def _record_to_dict(r: TrackRecord) -> Dict[str, Any]:
        return {
            "driver_name": r.driver_name,
            "lap_time": r.lap_time,
            "track_name": r.track_name,
            "date": r.date,
            "vehicle": r.vehicle,
            "class_name": r.class_name,
        }


__all__ = ["SpeedHiveClient", "SpeedHiveAPIError"]
