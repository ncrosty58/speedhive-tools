
# speedhive_tools/client.py
from __future__ import annotations

import time
import re
import csv
import json
from typing import Dict, List, Optional, Any, Iterable, Union
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone

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
        self.session = requests.Session()

    # ---------------- Internal helpers ----------------

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

    # ---------------- Public helper ----------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict | List:
        url = self._build_url(path)
        attempt = 0

        while True:
            try:
                resp = self.session.request(
                    method.upper(), url,
                    params=(params or {}),
                    json=json,
                    headers=self._headers(headers),
                    timeout=self.timeout,
                )

                if resp.status_code >= 400:
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
                        status=resp.status_code, url=url,
                    )

                try:
                    data = resp.json()
                except Exception:
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

    # ---------------- Public API ----------------

    def get_organization(self, org_id: int) -> Organization:
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
        auto_paginate: bool = False,
    ) -> List[EventResult]:
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
            MAX_PAGES = 2
            cur = 1
            while cur <= MAX_PAGES:
                page_rows = fetch_one(per_page, cur)
                if not page_rows:
                    break
                rows.extend(page_rows)
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
        data = self._get(f"/events/{event_id}/results")

        if isinstance(data, dict):
            candidate = data.get("event") or data.get("result") or data
            if isinstance(candidate, dict):
                merged = dict(candidate)
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

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    return event_result_from_api(item)
            raise SpeedHiveAPIError(
                f"Unexpected list payload for event {event_id}",
                url=self._build_url(f"/events/{event_id}/results"),
            )

        raise SpeedHiveAPIError(
            f"Unexpected payload type for event {event_id}",
            url=self._build_url(f"/events/{event_id}/results"),
        )

    def get_track_records_by_org(self, org_id: int) -> List[TrackRecord]:
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

    # ---------------- Export helpers ----------------

    def export_records_to_json(self, org_or_records: Union[int, Iterable[TrackRecord]], out_path: str | Path) -> int:
        if isinstance(org_or_records, int):
            records = self.get_track_records_by_org(org_or_records)
        else:
            records = list(org_or_records)
        payload = {"records": [self._record_to_dict(r) for r in records]}
        Path(out_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return len(records)

    def export_records_to_csv(self, org_or_records: Union[int, Iterable[TrackRecord]], out_path: str | Path) -> int:
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

    # ---- camelCase JSON exporter (includes sessionId) ----
    @staticmethod
    def _record_to_camel_dict(r: TrackRecord) -> Dict[str, Any]:
        sess_id = None
        try:
            if isinstance(getattr(r, "extra", None), dict):
                sess_id = r.extra.get("sessionId")
        except Exception:
            pass

        return {
            "classAbbreviation": r.class_name or "",
            "lapTime": r.lap_time or "",
            "driverName": r.driver_name or "",
            "marque": r.vehicle,
            "date": r.date,
            "trackName": r.track_name,
            "sessionId": sess_id,
        }

    def export_records_to_json_camel(self, org_or_records: Union[int, Iterable[TrackRecord]], out_path: str | Path) -> int:
        if isinstance(org_or_records, int):
            records = self.get_track_records_by_org(org_or_records)
        else:
            records = list(org_or_records)
        payload = {"records": [self._record_to_camel_dict(r) for r in records]}
        Path(out_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return len(records)

    # ---------------- Date helpers (derive event date) ----------------

    def _to_dt(self, s: str | None) -> datetime | None:
        if not isinstance(s, str) or not s.strip():
            return None
        s = s.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            try:
                dt = datetime.strptime(s, "%Y-%m-%d")
                dt = dt.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _event_start_dt(self, ev: dict) -> datetime | None:
        for k in ("startDateTime", "startTime", "start_date_time", "startDate", "start_date", "date", "eventDate"):
            v = ev.get(k)
            dt = self._to_dt(v if isinstance(v, str) else (str(v) if v is not None else None))
            if dt:
                return dt
        timing = ev.get("timing") or ev.get("schedule") or {}
        if isinstance(timing, dict):
            for k in ("start", "startTime", "startDateTime"):
                v = timing.get(k)
                dt = self._to_dt(v if isinstance(v, str) else (str(v) if v is not None else None))
                if dt:
                    return dt
        return None

    @staticmethod
    def _to_iso_date(dt: datetime | None) -> str | None:
        return dt.date().isoformat() if isinstance(dt, datetime) else None

    @staticmethod
    def _track_name_from_event_session(ev: dict, sess: dict) -> str | None:
        for d in (ev, sess):
            for k in ("trackName", "circuitName", "track", "circuit", "venue", "location"):
                v = d.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        loc = ev.get("location") or sess.get("location")
        if isinstance(loc, dict):
            for k in ("name", "trackName", "circuitName"):
                v = loc.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        return None

    # ---------------- Announcements (single-pass) ----------------

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
            if not isinstance(r.get("text"), str) or not r["text"].strip():
                r["text"] = self.get_announcement_text(r)
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

                event_dt = self._event_start_dt(ev)
                event_date_iso = self._to_iso_date(event_dt)
                track_name = self._track_name_from_event_session(ev, s)

                rows = self.get_session_announcements(sid)
                for r in rows:
                    r["eventId"] = ev_id
                    r["eventName"] = ev.get("name")
                    r["sessionName"] = s.get("name")
                    r["eventDate"] = event_date_iso
                    r["trackName"] = r.get("trackName") or track_name
                all_rows.extend(rows)

        return all_rows

    # ---------------- Detection & parsing ----------------

    # Accept "New Track Record" and "New Class Record"; still allow bare "Track Record"
    _TR_PATTERNS = [
        r"(?i)\bNew\s+Track\s+Record\b",
        r"(?i)\bNew\s+Class\s+Record\b",
        r"(?i)\bTrack\s+Record\b",
    ]
    # Deny-list phrases indicating the announcement is *not* an official record
    _NEGATION_PATTERNS = [
        r"(?i)\bnot\s+counted\b",
        r"(?i)\bunofficial\b",
        r"(?i)\bexhibition\b",
        r"(?i)\bnot\s+recognized\b",
    ]

    def find_track_record_announcements(self, text: str) -> bool:
        if not text:
            return False
        if any(re.search(p, text) for p in self._NEGATION_PATTERNS):
            return False
        return any(re.search(p, text) for p in self._TR_PATTERNS)

    def looks_like_record_without_prefix(self, text: str) -> bool:
        """Heuristic: entry looks like '(time) for CLASS by DRIVER' but lacks 'New ... Record' prefix."""
        if not isinstance(text, str):
            return False
        TIME_MMSS = r"\b\d{1,2}:\d{2}\.\d{3}\b"
        CLASS_ABBR = r"\b[A-Z]{1,4}(?:-[A-Z0-9]{1,3})?\b"
        raw = text.strip()
        patterns = [
            re.compile(rf"(?i)^\s*\(\s*({TIME_MMSS})\s*\)\s*for\s+({CLASS_ABBR})\s+by\s+(.+?)\s*[.!]?\s*$"),
            re.compile(rf"(?i)^\s*({TIME_MMSS})\s*for\s+({CLASS_ABBR})\s+by\s+(.+?)\s*[.!]?\s*$"),
        ]
        return any(p.search(raw) for p in patterns)

    def get_announcement_text(self, row: Dict) -> str:
        for k in ("text", "message", "content", "announcement", "value", "body"):
            v = row.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for k in ("cells", "columns", "data", "values"):
            v = row.get(k)
            if isinstance(v, list):
                strings = [s.strip() for s in v if isinstance(s, str) and s.strip()]
                if strings:
                    return sorted(strings, key=len, reverse=True)[0]
        strings = [str(v).strip() for v in row.values() if isinstance(v, str) and str(v).strip()]
        return sorted(strings, key=len, reverse=True)[0] if strings else ""

    def parse_track_record_announcement(self, row: Dict) -> Optional[TrackRecord]:
        text = self.get_announcement_text(row)
        if not self.find_track_record_announcements(text):
            return None

        TIME_MMSS = r"\b\d{1,2}:\d{2}\.\d{3}\b"
        CLASS_ABBR = r"\b[A-Z]{1,4}(?:-[A-Z0-9]{1,3})?\b"
        DATE_PATTERNS = [
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b[A-Za-z]{3,9} \d{1,2}, \d{4}\b",
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        ]
        PAREN_CONTENT = r"\(([^)]+)\)"
        SEPS = r"[\-–—•]"

        def _norm(s: str) -> str:
            return re.sub(r"\s+", " ", s or "").strip()

        raw = _norm(text)
        PREFIX = r"(?i)New\s+(?:Track|Class)\s+Record"  # accept both Track and Class

        # "(time) for CLASS by DRIVER in MARQUE."
        RE_FOR_BY_IN = re.compile(
            rf"{PREFIX}\s*\(\s*({TIME_MMSS})\s*\)\s*for\s+({CLASS_ABBR})\s+by\s+(.+?)\s+in\s+(.+?)(?:[.!]\s*$|\s*$)"
        )
        m = RE_FOR_BY_IN.search(raw)
        if m:
            lap_time, class_abbr, driver_raw, marque = m.groups()
            return TrackRecord(
                driver_name=_norm(driver_raw),
                lap_time=_norm(lap_time),
                track_name=row.get("trackName"),
                date=row.get("eventDate"),
                vehicle=_norm(marque),
                class_name=_norm(class_abbr),
                extra={**row, "announcementText": raw},
            )

        # "(time) for CLASS by DRIVER."
        RE_FOR_BY = re.compile(
            rf"{PREFIX}\s*\(\s*({TIME_MMSS})\s*\)\s*for\s+({CLASS_ABBR})\s+by\s+(.+?)(?:[.!]\s*$|\s*$)"
        )
        m = RE_FOR_BY.search(raw)
        if m:
            lap_time, class_abbr, driver_raw = m.groups()
            return TrackRecord(
                driver_name=_norm(driver_raw),
                lap_time=_norm(lap_time),
                track_name=row.get("trackName"),
                date=row.get("eventDate"),
                vehicle=None,
                class_name=_norm(class_abbr),
                extra={**row, "announcementText": raw},
            )

        # "time for CLASS by DRIVER" (no parentheses)
        RE_FOR_BY_NOPAREN = re.compile(
            rf"{PREFIX}\s*({TIME_MMSS})\s*for\s+({CLASS_ABBR})\s+by\s+(.+?)(?:[.!]\s*$|\s*$)"
        )
        m = RE_FOR_BY_NOPAREN.search(raw)
        if m:
            lap_time, class_abbr, driver_raw = m.groups()
            return TrackRecord(
                driver_name=_norm(driver_raw),
                lap_time=_norm(lap_time),
                track_name=row.get("trackName"),
                date=row.get("eventDate"),
                vehicle=None,
                class_name=_norm(class_abbr),
                extra={**row, "announcementText": raw},
            )

        # Separator-based primary (CLASS – TIME – DRIVER – (MARQUE) – DATE)
        primary = re.compile(
            rf"{PREFIX}.*?"
            rf"{SEPS}\s*({CLASS_ABBR})\s*{SEPS}\s*({TIME_MMSS})"
            rf"\s*{SEPS}\s*(.+?)\s*(?:{PAREN_CONTENT})?"
            rf"(?:\s*{SEPS}\s*({'|'.join(DATE_PATTERNS)}))?",
        )
        m = primary.search(raw)
        if m:
            class_abbr, lap_time, driver_raw, maybe_marque, maybe_date = (list(m.groups()) + ["", ""])[:5]

            final_date = row.get("eventDate")
            if not final_date and maybe_date:
                for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%d/%m/%Y"):
                    try:
                        final_date = datetime.strptime(maybe_date.strip(), fmt).date().isoformat()
                        break
                    except ValueError:
                        pass

            return TrackRecord(
                driver_name=_norm(driver_raw),
                lap_time=_norm(lap_time),
                track_name=row.get("trackName"),
                date=final_date,
                vehicle=_norm(maybe_marque) if maybe_marque else None,
                class_name=_norm(class_abbr),
                extra={**row, "announcementText": raw},
            )

        # Alternate separator (DRIVER – TIME – CLASS – (DATE))
        alternate = re.compile(
            rf"{PREFIX}.*?"
            rf"\s*(.+?)\s*(?:{PAREN_CONTENT})?\s*{SEPS}\s*({TIME_MMSS})"
            rf"\s*{SEPS}\s*({CLASS_ABBR})"
            rf"(?:\s*{SEPS}\s*({'|'.join(DATE_PATTERNS)}))?",
        )
        m = alternate.search(raw)
        if m:
            driver_raw, maybe_marque, lap_time, class_abbr, maybe_date = (list(m.groups()) + [""])[:5]

            final_date = row.get("eventDate")
            if not final_date and maybe_date:
                for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%d/%m/%Y"):
                    try:
                        final_date = datetime.strptime(maybe_date.strip(), fmt).date().isoformat()
                        break
                    except ValueError:
                        pass

            return TrackRecord(
                driver_name=_norm(driver_raw),
                lap_time=_norm(lap_time),
                track_name=row.get("trackName"),
                date=final_date,
                vehicle=_norm(maybe_marque) if maybe_marque else None,
                class_name=_norm(class_abbr),
                extra={**row, "announcementText": raw},
            )

        # Fallback anchored on lap time
        find_time = re.compile(TIME_MMSS)
        tf = find_time.search(raw)
        if tf:
            lap_time = tf.group(0)
            tokens = [_norm(t) for t in re.split(SEPS, raw) if t.strip()]
            class_abbr = next((t for t in tokens if re.fullmatch(CLASS_ABBR, t)), None)

            date_iso = row.get("eventDate")
            if not date_iso:
                for t in tokens:
                    for dp in DATE_PATTERNS:
                        d = re.search(dp, t)
                        if d:
                            s = d.group(0)
                            for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%d/%m/%Y"):
                                try:
                                    date_iso = datetime.strptime(s, fmt).date().isoformat()
                                    break
                                except ValueError:
                                    pass
                            if date_iso:
                                break
                    if date_iso:
                        break

            marque = None
            for t in tokens:
                mm = re.search(PAREN_CONTENT, t)
                if mm:
                    marque = _norm(mm.group(1))
                    break

            def is_date_token(t: str) -> bool:
                DATE_PATTERNS_LOCAL = [
                    r"\b\d{4}-\d{2}-\d{2}\b",
                    r"\b[A-Za-z]{3,9} \d{1,2}, \d{4}\b",
                    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                ]
                return any(re.search(dp, t) for dp in DATE_PATTERNS_LOCAL)

            candidates = [
                t for t in tokens
                if t != lap_time and t != class_abbr
                and not is_date_token(t)
                and not re.search(PAREN_CONTENT, t)
                and "New Track Record" not in t
                and "New Class Record" not in t
            ]
            driver = (_norm(sorted(candidates, key=len, reverse=True)[0]) if candidates else "")

            if class_abbr or driver or marque or date_iso:
                return TrackRecord(
                    driver_name=driver,
                    lap_time=lap_time,
                    track_name=row.get("trackName"),
                    date=date_iso,
                    vehicle=marque,
                    class_name=(class_abbr or ""),
                    extra={**row, "announcementText": raw},
                )

        return None

    # ---------------- Validation & mapping ----------------

    @staticmethod
    def is_record_valid(tr: TrackRecord) -> tuple[bool, str | None]:
        if not tr:
            return False, "Parser returned None"
        if not (tr.lap_time and isinstance(tr.lap_time, str)):
            return False, "Missing lapTime"
        if not (tr.class_name and tr.class_name.strip()):
            return False, "Missing classAbbreviation"
        if not (tr.driver_name and tr.driver_name.strip()):
            return False, "Missing driverName"
        if isinstance(tr.vehicle, str) and tr.vehicle.strip() == tr.lap_time.strip():
            return False, "Marque equals lapTime (malformed text)"
        return True, None

    def get_track_records_from_org_announcements(self, org_id: int) -> List[TrackRecord]:
        rows = self.get_all_session_announcements_for_org(org_id)
        records: List[TrackRecord] = []
        for r in rows:
            tr = self.parse_track_record_announcement(r)
            if tr:
                records.append(tr)
        return records

    # ---------------- Record mapping helpers ----------------

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
