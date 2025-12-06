
# speedhive_tools/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List


# -----------------------------
# Core dataclasses (snake_case fields for tests)
# -----------------------------

@dataclass
class Organization:
    # Tests expect org_id (snake_case). Keep id optional for convenience.
    org_id: Optional[int] = None
    name: str = ""
    city: Optional[str] = None
    country: Optional[str] = None
    logo: Optional[str] = None
    url: Optional[str] = None
    # Optional camelCase for internal use if needed
    id: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Location:
    id: Optional[int] = None
    name: Optional[str] = None
    length: Optional[float] = None
    lengthUnit: Optional[str] = None
    lengthLabel: Optional[str] = None
    country: Optional[str] = None
    lon: Optional[float] = None
    lat: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventResult:
    # Tests expect event_id and event_name (snake_case)
    event_id: Optional[int] = None
    event_name: str = ""           # tests read EventResult.event_name
    sport: Optional[str] = None
    startDate: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    location: Optional[Location] = None
    organization: Optional[Organization] = None

    # Records (tests access EventResult.records)
    records: List[Dict[str, Any]] = field(default_factory=list)

    # Optional camelCase/legacy fields for convenience
    id: Optional[int] = None
    name: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrackRecord:
    # Snake_case fields expected by tests
    driver_name: str
    lap_time: Optional[float | str] = None
    track_name: Optional[str] = None
    date: Optional[str] = None
    vehicle: Optional[str] = None
    class_name: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


# -----------------------------
# Helpers: API JSON → dataclasses
# -----------------------------

def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    try:
        # Handle ISO strings that end with 'Z'
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def organization_from_api(d: Dict[str, Any]) -> Organization:
    country = d.get("country")
    country_name = country.get("name") if isinstance(country, dict) else country
    # Accept either 'org_id' or 'id'
    org_id = d.get("org_id", d.get("id"))
    return Organization(
        org_id=org_id,
        name=d.get("name") or d.get("org_name") or "",
        city=d.get("city"),
        country=country_name,
        logo=d.get("logo"),
        url=d.get("url"),
        id=d.get("id"),
        extra={k: v for k, v in d.items() if k not in {"org_id", "id", "name", "org_name", "city", "country", "logo", "url"}},
    )


def location_from_api(d: Dict[str, Any]) -> Location:
    country = d.get("country")
    country_name = country.get("name") if isinstance(country, dict) else country
    return Location(
        id=d.get("id"),
        name=d.get("name"),
        length=d.get("length"),
        lengthUnit=d.get("lengthUnit"),
        lengthLabel=d.get("lengthLabel"),
        country=country_name,
        lon=d.get("lon"),
        lat=d.get("lat"),
        extra={k: v for k, v in d.items() if k not in {
            "id", "name", "length", "lengthUnit", "lengthLabel", "country", "lon", "lat"
        }},
    )


def event_result_from_api(d: Dict[str, Any]) -> EventResult:
    """
    Map a generic event payload to EventResult.
    Accepts either:
      - snake_case: event_id / event_name / records
      - camelCase:  id / name
      - list-like fields: items / results → records
    """
    loc = d.get("location")
    org = d.get("organization")

    # IDs and names (support both variants)
    event_id = d.get("event_id", d.get("id"))
    event_name = d.get("event_name", d.get("name") or "")

    # Records (prefer explicit 'records', then 'items', then 'results', then 'data')
    records = []
    for key in ("records", "items", "results", "data"):
        val = d.get(key)
        if isinstance(val, list):
            records = val
            break

    return EventResult(
        event_id=event_id,
        event_name=event_name,
        sport=d.get("sport"),
        startDate=_parse_dt(d.get("startDate")),
        updatedAt=_parse_dt(d.get("updatedAt")),
        location=location_from_api(loc) if isinstance(loc, dict) else None,
        organization=organization_from_api(org) if isinstance(org, dict) else None,
        records=records,
        id=d.get("id"),
        name=d.get("name"),
        extra={k: v for k, v in d.items() if k not in {
            "event_id", "id", "event_name", "name", "sport",
            "startDate", "updatedAt", "location", "organization",
            "records", "items", "results", "data"
        }},
    )


__all__ = [
    "Organization",
    "Location",
    "EventResult",
    "TrackRecord",
    "organization_from_api",
    "location_from_api",
    "event_result_from_api",
]
