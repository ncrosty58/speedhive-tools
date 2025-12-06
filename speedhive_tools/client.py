
# speedhive_tools/client.py
from __future__ import annotations
import time
import re
import csv
import json
from typing import Dict, List, Optional, Any, Iterable, Union, Iterator, Tuple
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# NOTE: these imports are from your package; keep them as in your repo
from .models import (
    Organization,
    EventResult,
    TrackRecord,
    organization_from_api,
    event_result_from_api,
)
from .utils import parse_date, format_seconds_to_lap_time  # <-- added import


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

# Default to the working Event Results base; tests can override via base_url.
DEFAULT_BASE_URL = "https://eventresults-api.speedhive.com/api/v0.2.3/eventresults"


class SpeedHiveClient:
    def __init__(
        self,
        api_key: str | None = None,
        rate_delay: float = 0.0,  # optional small pacing between batches (not per request)
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 30,
        retries: int = 2,
        pool_connections: int = 20,
        pool_maxsize: int = 40,
    ):
        self.api_key = api_key
        self.rate_delay = max(0.0, float(rate_delay))
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, int(retries))

        # Detect path family based on hostname (EXACT match), not substring.
        parsed = urlparse(self.base_url)
        host = (parsed.netloc or "").lower()
        if host == "api.speedhive.com":
            self._path_family = "orgs"
        else:
            # eventresults-api.speedhive.com and anything else → organizations
            self._path_family = "organizations"

        # Pooled session with centralized headers.
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        if self.api_key:
            self.session.headers["Apikey"] = self.api_key

        # Robust retry/backoff policy (idempotent methods only).
        retry = Retry(
            total=self.retries,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD", "OPTIONS"),
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    # ------------------------ Internal helpers ------------------------

    def _orgs_prefix(self) -> str:
        return "orgs" if self._path_family == "orgs" else "organizations"

    def _build_url(self, path: str) -> str:
        if path.startswith("/"):
            return f"{self.base_url}{path}"
        return urljoin(self.base_url + "/", path)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict | List:
        """Centralized request with pooled session and retry/backoff."""
        url = self._build_url(path)
        try:
            req_headers = None
            if headers:
                req_headers = dict(self.session.headers)
                req_headers.update(headers)
            resp = self.session.request(
                method.upper(),
                url,
                params=(params or {}),
                json=json,
                headers=req_headers,
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise SpeedHiveAPIError(f"Network error calling {url}: {e}", url=url) from e

        if resp.status_code >= 400:
            preview = ""
            try:
                preview = (resp.text or "").strip()[:400]
            except Exception:
                preview = ""
            raise SpeedHiveAPIError(
                f"HTTP {resp.status_code} for {url}: {preview}",
                status=resp.status_code,
                url=url,
            )

        # 204 No Content → return empty dict
        if resp.status_code == 204:
            return {}

        # Parse JSON; if invalid, raise "Invalid JSON response".
        try:
            return resp.json()
        except Exception:
            raise SpeedHiveAPIError("Invalid JSON response", status=resp.status_code, url=url)

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict | List:
        return self._request("GET", path, params=params)

    # ------------------------ Pagination helpers ------------------------

    # Offset/count paginator (for 'organizations' family)
    def _paginate_offset(
        self,
        path: str,
        *,
        count: int = 200,
        start_offset: int = 0,
        params: Optional[dict] = None,
        max_items: Optional[int] = None,
    ) -> Iterator[Dict]:
        """Yield items from an offset/count endpoint until exhausted (sequential)."""
        offset = start_offset
        yielded = 0
        while True:
            q = dict(params or {})
            q.update({"count": count, "offset": offset})
            data = self._get(path, params=q)

            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("items") or data.get("events") or data.get("rows") or []
            else:
                items = []

            if not isinstance(items, list) or not items:
                break

            for it in items:
                yield it
                yielded += 1
                if max_items is not None and yielded >= max_items:
                    return

            if len(items) < count:
                break

            offset += count
            if self.rate_delay:
                time.sleep(self.rate_delay)

    # Page/per_page paginator (for 'orgs' family, respecting totalPages)
    def _paginate_pages(
        self,
        path: str,
        *,
        per_page: int = 50,
        start_page: int = 1,
        params: Optional[dict] = None,
    ) -> List[Dict]:
        """Fetch all pages using per_page/page until totalPages is reached."""
        # First request to learn totalPages
        q = dict(params or {})
        q.update({"per_page": per_page, "page": start_page})
        data = self._get(path, params=q)

        # If API returns a list directly, just return it
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []

        items = data.get("items") or []
        total_pages = data.get("totalPages") or data.get("total_pages") or 1
        all_items: List[Dict] = []
        all_items.extend(items)

        # Fetch remaining pages 2..total_pages
        for page in range(start_page + 1, int(total_pages) + 1):
            q = dict(params or {})
            q.update({"per_page": per_page, "page": page})
            d = self._get(path, params=q)
            if isinstance(d, list):
                all_items.extend(d)
                break
            elif isinstance(d, dict):
                batch = d.get("items") or []
                if not batch:
                    break
                all_items.extend(batch)
            else:
                break
            if self.rate_delay:
                time.sleep(self.rate_delay)
        return all_items

    # ------------------------ Public API ------------------------

    def get_organization(self, org_id: int) -> Organization:
        data = self._get(f"/{self._orgs_prefix()}/{org_id}")
        if not isinstance(data, dict):
            raise SpeedHiveAPIError(
                f"Unexpected payload for organization {org_id}",
                url=self._build_url(f"/{self._orgs_prefix()}/{org_id}"),
            )
        return organization_from_api(data)

    # Backwards-compatible 'list' variant for callers expecting a list of EventResult.
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
        """
        List events for an organization, supporting both page/per_page ('orgs') and
        offset/count ('organizations') styles, matching unit-test expectations.
        - For 'orgs': iterate pages until totalPages, even when auto_paginate=False.
        - For 'organizations': use offset/count iteration if auto_paginate=True,
          or single page (count/offset) if not.
        """
        events_raw: List[Dict] = []
        if self._path_family == "orgs":
            # Page/per_page style with totalPages
            ppg = per_page or 50
            start_p = page or 1
            items = self._paginate_pages(
                f"/{self._orgs_prefix()}/{org_id}/events",
                per_page=ppg,
                start_page=start_p,
            )
            events_raw = items if isinstance(items, list) else []
        else:
            # Offset/count style
            if auto_paginate:
                events_raw = list(
                    self._paginate_offset(
                        f"/{self._orgs_prefix()}/{org_id}/events",
                        count=count or (per_page or 200),
                        start_offset=offset or 0,
                        params=None,
                    )
                )
            else:
                # Single page
                q_count = count or (per_page or 200)
                q_off = offset or 0
                data = self._get(
                    f"/{self._orgs_prefix()}/{org_id}/events",
                    params={"count": q_count, "offset": q_off},
                )
                if isinstance(data, list):
                    events_raw = data
                elif isinstance(data, dict):
                    events_raw = data.get("items") or data.get("events") or []
                else:
                    events_raw = []

        # Map raw dicts to EventResult
        results: List[EventResult] = []
        for r in events_raw:
            if isinstance(r, dict):
                try:
                    results.append(event_result_from_api(r))
                except Exception:
                    continue
        return results

    def get_events_for_org(self, org_id: int, count: int = 200, offset: int = 0) -> List[Dict]:
        """Convenience list (raw dicts), adhering to the active path family."""
        if self._path_family == "orgs":
            # Page/per_page → single page only if caller requests it explicitly.
            data = self._get(
                f"/{self._orgs_prefix()}/{org_id}/events",
                params={"per_page": count, "page": 1},
            )
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("items") or []
            return []
        else:
            return list(
                self._paginate_offset(
                    f"/{self._orgs_prefix()}/{org_id}/events",
                    count=count,
                    start_offset=offset,
                    params=None,
                )
            )

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
        data = self._get(f"/{self._orgs_prefix()}/{org_id}/records")
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

    # ------------------------ Export helpers ------------------------

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

    def export_records_to_json_camel(self, org_or_records: Union[int, Iterable[TrackRecord]], out_path: str | Path) -> int:
        if isinstance(org_or_records, int):
            records = self.get_track_records_by_org(org_or_records)
        else:
            records = list(org_or_records)
        payload = {"records": [self._record_to_camel_dict(r) for r in records]}
        Path(out_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return len(records)

    # ------------------------ Announcements (sequential) ------------------------

    def get_sessions_for_event(self, event_id: int) -> List[Dict]:
        grouping = self._get(f"/events/{event_id}/sessions")
        result: List[Dict] = []

        def _collect(grouping_obj: Dict):
            for s in (grouping_obj.get("sessions", []) or []):
                result.append(s)
            for g in (grouping_obj.get("groups", []) or []):
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
        """Sequentially walk events -> sessions -> announcements and enrich rows."""
        all_rows: List[Dict] = []
        # Use appropriate iteration style for events
        if self._path_family == "orgs":
            events = self._paginate_pages(f"/{self._orgs_prefix()}/{org_id}/events", per_page=200, start_page=1)
        else:
            events = list(self._paginate_offset(f"/{self._orgs_prefix()}/{org_id}/events", count=200, start_offset=0))

        for ev in events:
            ev_id = ev.get("id") or ev.get("event_id") or ev.get("eventId")
            if not ev_id:
                continue
            sessions = self.get_sessions_for_event(int(ev_id))
            event_dt = self._event_start_dt(ev)
            event_date_iso = self._to_iso_date(event_dt)
            track_name = self._track_name_from_event_session(ev, {})
            for s in sessions:
                sid = s.get("id")
                if not sid:
                    continue
                rows = self.get_session_announcements(sid)
                for r in rows:
                    r["eventId"] = ev_id
                    r["eventName"] = ev.get("name") or ev.get("event_name")
                    r["sessionName"] = s.get("name")
                    r["eventDate"] = r.get("eventDate") or event_date_iso
                    r["trackName"] = r.get("trackName") or track_name
                all_rows.extend(rows)
            if self.rate_delay:
                time.sleep(self.rate_delay)
        return all_rows

    # ------------------------ Detection & parsing ------------------------

    _TR_PATTERNS = [
        re.compile(r"(?i)\bNew\s+Track\s+Record\b"),
        re.compile(r"(?i)\bNew\s+Class\s+Record\b"),
        re.compile(r"(?i)\bTrack\s+Record\b"),
    ]
    _NEGATION_PATTERNS = [
        re.compile(r"(?i)\bnot\s+counted\b"),
        re.compile(r"(?i)\bunofficial\b"),
        re.compile(r"(?i)\bexhibition\b"),
        re.compile(r"(?i)\bnot\s+recognized\b"),
    ]
    _TIME_MMSS = r"\b\d{1,2}:\d{2}\.\d{3}\b"
    # ✅ Allow letters AND digits in the first segment (fixes T2, T4, SM2, GT1, etc.)
    _CLASS_ABBR = r"\b[A-Z0-9]{1,4}(?:-[A-Z0-9]{1,3})?\b"
    _PAREN_CONTENT = r"\(\([^)]+\)\)"
    _SEPS = r"[\-\u2013\u2014\u2022]"
    _PREFIX = re.compile(r"(?i)New\s+(?:Track|Class)\s+Record")
    RE_FOR_BY_IN = re.compile(
        rf"{_PREFIX.pattern}\s*\(\s*({_TIME_MMSS})\s*\)\s*for\s+({_CLASS_ABBR})\s+by\s+(.+?)\s+in\s+(.+?)(?:[.!]\s*$|\s*$)"
    )
    RE_FOR_BY = re.compile(
        rf"{_PREFIX.pattern}\s*\(\s*({_TIME_MMSS})\s*\)\s*for\s+({_CLASS_ABBR})\s+by\s+(.+?)(?:[.!]\s*$|\s*$)"
    )
    RE_FOR_BY_NOPAREN = re.compile(
        rf"{_PREFIX.pattern}\s*({_TIME_MMSS})\s*for\s+({_CLASS_ABBR})\s+by\s+(.+?)(?:[.!]\s*$|\s*$)"
    )
    PRIMARY = re.compile(
        rf"{_PREFIX.pattern}.*?"
        rf"{_SEPS}\s*({_CLASS_ABBR})\s*{_SEPS}\s*({_TIME_MMSS})"
        rf"\s*{_SEPS}\s*(.+?)\s*(?:{_PAREN_CONTENT})?"
        rf"(?:\s*{_SEPS}\s*("
        r"\b\d{4}-\d{2}-\d{2}\b|"
        r"\b[A-Za-z]{3,9} \d{1,2}, \d{4}\b|"
        r"\b\d{1,2}/\d{1,2}/\d{4}\b"
        r"))?"
    )
    ALTERNATE = re.compile(
        rf"{_PREFIX.pattern}.*?"
        rf"\s*(.+?)\s*(?:{_PAREN_CONTENT})?\s*{_SEPS}\s*({_TIME_MMSS})"
        rf"\s*{_SEPS}\s*({_CLASS_ABBR})"
        rf"(?:\s*{_SEPS}\s*("
        r"\b\d{4}-\d{2}-\d{2}\b|"
        r"\b[A-Za-z]{3,9} \d{1,2}, \d{4}\b|"
        r"\b\d{1,2}/\d{1,2}/\d{4}\b"
        r"))?"
    )
    FIND_TIME = re.compile(_TIME_MMSS)
    CLASS_FULL = re.compile(f"^{_CLASS_ABBR}$")
    SEPARATOR_SPLIT = re.compile(_SEPS)

    def find_track_record_announcements(self, text: str) -> bool:
        if not text:
            return False
        if any(p.search(text) for p in self._NEGATION_PATTERNS):
            return False
        return any(p.search(text) for p in self._TR_PATTERNS)

    def looks_like_record_without_prefix(self, text: str) -> bool:
        """Heuristic: entry looks like '(time) for CLASS by DRIVER' but lacks 'New ... Record' prefix."""
        if not isinstance(text, str):
            return False
        raw = text.strip()
        patterns = [
            re.compile(
                rf"(?i)^\s*\(\s*({self._TIME_MMSS})\s*\)\s*for\s+({self._CLASS_ABBR})\s+by\s+(.+?)\s*[.!]?\s*$"
            ),
            re.compile(
                rf"(?i)^\s*({self._TIME_MMSS})\s*for\s+({self._CLASS_ABBR})\s+by\s+(.+?)\s*[.!]?\s*$"
            ),
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
        raw = re.sub(r"\s+", " ", (self.get_announcement_text(row) or "")).strip()
        if not self.find_track_record_announcements(raw):
            return None

        # New (time) for CLASS by DRIVER in MARQUE.
        m = self.RE_FOR_BY_IN.search(raw)
        if m:
            lap_time, class_abbr, driver_raw, marque = m.groups()
            # Strip grid positions like "[2]" from driver names
            driver_clean = re.sub(r"\[\s*\d+\s*\]\s*", "", driver_raw).strip()
            return TrackRecord(
                driver_name=driver_clean,
                lap_time=lap_time.strip(),
                track_name=row.get("trackName"),
                date=row.get("eventDate"),
                vehicle=marque.strip(),
                class_name=class_abbr.strip(),
                extra={**row, "announcementText": raw},
            )

        # New (time) for CLASS by DRIVER.
        m = self.RE_FOR_BY.search(raw)
        if m:
            lap_time, class_abbr, driver_raw = m.groups()
            driver_clean = re.sub(r"\[\s*\d+\s*\]\s*", "", driver_raw).strip()
            return TrackRecord(
                driver_name=driver_clean,
                lap_time=lap_time.strip(),
                track_name=row.get("trackName"),
                date=row.get("eventDate"),
                vehicle=None,
                class_name=class_abbr.strip(),
                extra={**row, "announcementText": raw},
            )

        # New time for CLASS by DRIVER (no parentheses around time)
        m = self.RE_FOR_BY_NOPAREN.search(raw)
        if m:
            lap_time, class_abbr, driver_raw = m.groups()
            driver_clean = re.sub(r"\[\s*\d+\s*\]\s*", "", driver_raw).strip()
            return TrackRecord(
                driver_name=driver_clean,
                lap_time=lap_time.strip(),
                track_name=row.get("trackName"),
                date=row.get("eventDate"),
                vehicle=None,
                class_name=class_abbr.strip(),
                extra={**row, "announcementText": raw},
            )

        # Separator-based primary (CLASS – TIME – DRIVER – (MARQUE) – DATE)
        m = self.PRIMARY.search(raw)
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
            driver_clean = re.sub(r"\[\s*\d+\s*\]\s*", "", driver_raw).strip()
            return TrackRecord(
                driver_name=driver_clean,
                lap_time=lap_time.strip(),
                track_name=row.get("trackName"),
                date=final_date,
                vehicle=(maybe_marque.strip() if maybe_marque else None),
                class_name=class_abbr.strip(),
                extra={**row, "announcementText": raw},
            )

        # Alternate separator (DRIVER – TIME – CLASS – (DATE))
        m = self.ALTERNATE.search(raw)
        if m:
            driver_raw, maybe_marque, lap_time, class_abbr, maybe_date = (list(m.groups()) + [""])[0:5]
            final_date = row.get("eventDate")
            if not final_date and maybe_date:
                for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%d/%m/%Y"):
                    try:
                        final_date = datetime.strptime(maybe_date.strip(), fmt).date().isoformat()
                        break
                    except ValueError:
                        pass
            driver_clean = re.sub(r"\[\s*\d+\s*\]\s*", "", driver_raw).strip()
            return TrackRecord(
                driver_name=driver_clean,
                lap_time=lap_time.strip(),
                track_name=row.get("trackName"),
                date=final_date,
                vehicle=(maybe_marque.strip() if maybe_marque else None),
                class_name=class_abbr.strip(),
                extra={**row, "announcementText": raw},
            )

        # Fallback anchored on lap time
        tf = self.FIND_TIME.search(raw)
        if tf:
            lap_time = tf.group(0)
            tokens = [t.strip() for t in self.SEPARATOR_SPLIT.split(raw) if t.strip()]
            class_abbr = next((t for t in tokens if self.CLASS_FULL.fullmatch(t)), None)
            date_iso = row.get("eventDate")
            if not date_iso:
                for t in tokens:
                    for dp in (
                        r"\b\d{4}-\d{2}-\d{2}\b",
                        r"\b[A-Za-z]{3,9} \d{1,2}, \d{4}\b",
                        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                    ):
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
                mm = re.search(self._PAREN_CONTENT, t)
                if mm:
                    marque = mm.group(1).strip()
                    break

            def is_date_token(t: str) -> bool:
                return any(re.search(dp, t) for dp in (
                    r"\b\d{4}-\d{2}-\d{2}\b",
                    r"\b[A-Za-z]{3,9} \d{1,2}, \d{4}\b",
                    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                ))

            candidates = [
                t for t in tokens
                if t != lap_time and t != class_abbr
                and not is_date_token(t)
                and not re.search(self._PAREN_CONTENT, t)
                and "New Track Record" not in t
                and "New Class Record" not in t
            ]
            driver = (sorted(candidates, key=len, reverse=True)[0].strip() if candidates else "")
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

    # ------------------------ Validation ------------------------

    def is_record_valid(self, tr: TrackRecord | None) -> Tuple[bool, str | None]:
        """
        Minimal structural validation for a parsed TrackRecord.
        Returns (ok, reason). Reasons are short, stable strings used by callers.
        """
        if tr is None:
            return False, "No record parsed"
        # lapTime must be present and match mm:ss.mmm (e.g., 1:12.806)
        if not tr.lap_time or not re.fullmatch(r"\d{1,2}:\d{2}\.\d{3}", str(tr.lap_time)):
            return False, "Invalid lapTime"
        # driverName required
        if not isinstance(tr.driver_name, str) or not tr.driver_name.strip():
            return False, "Missing driverName"
        # trackName required
        if not isinstance(tr.track_name, str) or not tr.track_name.strip():
            return False, "Missing trackName"
        # classAbbreviation required (caller may choose to accept blank downstream)
        if not isinstance(tr.class_name, str) or not tr.class_name.strip():
            return False, "Missing classAbbreviation"
        # date is helpful but may be inferred elsewhere; don’t hard‑fail if absent.
        return True, None

    # ------------------------ Helpers used above ------------------------

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

    def _to_dt(self, s: str | None) -> datetime | None:
        if not isinstance(s, str) or not s.strip():
            return None
        try:
            return parse_date(s, tz_aware=True)
        except ValueError:
            return None

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
        # Leave lap_time ‘as‑is’ for non‑camel JSON/CSV to avoid changing existing behavior.
        return {
            "driver_name": r.driver_name,
            "lap_time": r.lap_time,
            "track_name": r.track_name,
            "date": r.date,
            "vehicle": r.vehicle,
            "class_name": r.class_name,
        }

    @staticmethod
    def _normalize_lap_time_str(value: Any) -> str:
        """
        Ensure lap time is in 'M:SS.mmm' format for camelCase export.
        - If it already matches that pattern, return as‑is.
        - Else, try to parse as seconds (float) and format.
        - If parsing fails, return the original string.
        """
        if value is None:
            return ""
        s = str(value).strip()
        if re.fullmatch(r"\d{1,2}:\d{2}\.\d{3}", s):
            return s
        try:
            secs = float(s)
            return format_seconds_to_lap_time(secs)
        except Exception:
            return s

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
            "lapTime": SpeedHiveClient._normalize_lap_time_str(r.lap_time),  # <-- normalized
            "driverName": r.driver_name or "",
            "marque": r.vehicle,
            "date": r.date,
            "trackName": r.track_name,
            "sessionId": sess_id,
        }

    # ------------------------ NEW: Global events feed ------------------------

    def iter_global_events(
        self,
        *,
        sport: str = "All",
        sport_category: str = "Motorized",
        count: int = 200,
        start_offset: int = 0,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Iterator[Dict]:
        """
        Yield raw event rows from the global /events feed with filters applied.
        Low‑RAM streaming: an iterator over dicts.
        """
        params: Dict[str, Any] = {"sport": sport, "sportCategory": sport_category}
        if extra_params:
            params.update(extra_params)

        yield from self._paginate_offset(
            path="/events",
            count=count,
            start_offset=start_offset,
            params=params,
            max_items=None,
        )

    def list_global_events(
        self,
        *,
        sport: str = "All",
        sport_category: str = "Motorized",
        count: int = 200,
        offset: int = 0,
        auto_paginate: bool = True,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> List[EventResult]:
        """
        Return a list of EventResult (mapped) from the global /events feed.
        Use auto_paginate=False for a single page.
        """
        params: Dict[str, Any] = {"sport": sport, "sportCategory": sport_category}
        if extra_params:
            params.update(extra_params)

        rows: List[Dict] = []
        if auto_paginate:
            rows = list(self._paginate_offset(
                path="/events",
                count=count,
                start_offset=offset,
                params=params,
                max_items=None,
            ))
        else:
            data = self._get("/events", params={"count": count, "offset": offset, **params})
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                rows = data.get("items") or data.get("events") or []
            else:
                rows = []

        results: List[EventResult] = []
        for r in rows:
            if isinstance(r, dict):
                try:
                    results.append(event_result_from_api(r))
                except Exception:
                    continue
        return results

    # ------------------------ OPTIONAL: streaming-friendly org iterators ------------------------

    def iter_organization_events(self, org_id: int, *, count: int = 200) -> Iterator[Dict]:
        """Yield raw org-scoped events using offset/count pagination."""
        yield from self._paginate_offset(
            path=f"/{self._orgs_prefix()}/{org_id}/events",
            count=count,
            start_offset=0,
            params=None,
            max_items=None,
        )


__all__ = ["SpeedHiveClient", "SpeedHiveAPIError"]
