
"""
models.py
Typed data models for the MYLAPS Speedhive Event Results API (public endpoints).

Endpoints covered (examples):
- List events across sport filters:
  GET /events?sport=All&sportCategory=Motorized&count=25&offset=0
- List events for an organization:
  GET /organizations/{ORG_ID}/events?count=25&offset=0&sportCategory=Motorized
- Get an event with sessions:
  GET /events/{EVENT_ID}?sessions=true
- List announcements (track records) for a session:
  GET /sessions/{SESSION_ID}/announcements

Design:
- Pydantic v2 models with aliases and robust parsing.
- Nested models for Country and Location (API returns dicts).
- Page wrappers normalize different shapes ("items", "events", raw lists).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _parse_lap_time_to_seconds(value: Optional[str | float]) -> Optional[float]:
    """
    Convert lap time to seconds if provided as string (HH:MM:SS(.sss), MM:SS(.sss), or SS(.sss)).
    Returns None if value is falsy or cannot be parsed.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s:
        return None

    parts = s.split(":")
    try:
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(s)
    except Exception:
        return None


# ------------------------------------------------------------------------------
# Nested Entities
# ------------------------------------------------------------------------------

class Country(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: Optional[int] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")
    alpha2: Optional[str] = Field(default=None, alias="alpha2")  # e.g., 'US', 'NZ', 'AU'


class Location(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: Optional[int] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")
    length_label: Optional[str] = Field(default=None, alias="lengthLabel")  # human-friendly text


# ------------------------------------------------------------------------------
# Core Entities
# ------------------------------------------------------------------------------

class Organization(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    org_id: Optional[int] = Field(default=None, alias="organizationId")
    id: Optional[int] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")
    short_name: Optional[str] = Field(default=None, alias="shortName")
    country: Optional[Country] = Field(default=None, alias="country")
    website: Optional[str] = Field(default=None, alias="website")
    logo_url: Optional[str] = Field(default=None, alias="logoUrl")

    @property
    def resolved_id(self) -> Optional[int]:
        return self.org_id or self.id

    @property
    def country_name(self) -> Optional[str]:
        return self.country.name if self.country else None


class Session(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    session_id: Optional[int] = Field(default=None, alias="sessionId")
    id: Optional[int] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")
    type: Optional[str] = Field(default=None, alias="type")  # e.g., "Race", "Practice"
    class_name: Optional[str] = Field(default=None, alias="className")
    group_name: Optional[str] = Field(default=None, alias="groupName")
    start_time: Optional[str] = Field(default=None, alias="startTime")
    end_time: Optional[str] = Field(default=None, alias="endTime")
    event_id: Optional[int] = Field(default=None, alias="eventId")
    status: Optional[str] = Field(default=None, alias="status")

    @property
    def resolved_id(self) -> Optional[int]:
        return self.session_id or self.id


class Event(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    event_id: Optional[int] = Field(default=None, alias="eventId")
    id: Optional[int] = Field(default=None, alias="id")
    event_name: Optional[str] = Field(default=None, alias="eventName")
    name: Optional[str] = Field(default=None, alias="name")
    location: Optional[Location] = Field(default=None, alias="location")
    track_name: Optional[str] = Field(default=None, alias="trackName")
    start_date: Optional[str] = Field(default=None, alias="startDate")
    end_date: Optional[str] = Field(default=None, alias="endDate")
    sport: Optional[str] = Field(default=None, alias="sport")
    sport_category: Optional[str] = Field(default=None, alias="sportCategory")
    status: Optional[str] = Field(default=None, alias="status")

    organization: Optional[Organization] = Field(default=None, alias="organization")
    sessions: Optional[List[Session]] = Field(default=None, alias="sessions")

    # --- NEW: normalize 'sessions' when it arrives as a dict/wrapper
    @model_validator(mode="before")
    @classmethod
    def _normalize_sessions(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        s = data.get("sessions")
        # If sessions is already a list, we're good
        if isinstance(s, list):
            return data

        # If sessions is a dict wrapper, try common keys
        if isinstance(s, dict):
            # Pattern 1: {"sessions": [...]}
            for key in ("sessions", "items", "list"):
                maybe = s.get(key)
                if isinstance(maybe, list):
                    new = dict(data)
                    new["sessions"] = maybe
                    return new

            # Pattern 2: {"groups": [{"sessions": [...]}, ...]}
            groups = s.get("groups")
            if isinstance(groups, list):
                collected: List[dict] = []
                for g in groups:
                    maybe = g.get("sessions")
                    if isinstance(maybe, list):
                        collected.extend(maybe)
                if collected:
                    new = dict(data)
                    new["sessions"] = collected
                    return new

            # Fallback: no recognizable list inside wrapper → set None
            new = dict(data)
            new["sessions"] = None
            return new

        # Any other unexpected shape → keep data; Pydantic will handle None
        return data

    @property
    def resolved_id(self) -> Optional[int]:
        return self.event_id or self.id

    @property
    def display_name(self) -> Optional[str]:
        return self.event_name or self.name

    @property
    def location_name(self) -> Optional[str]:
        return self.location.name if self.location else None


class Announcement(BaseModel):
    """
    Announcement/Track Record entry. The API may provide a message + structured fields.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Identifiers & meta
    id: Optional[int] = Field(default=None, alias="id")
    session_id: Optional[int] = Field(default=None, alias="sessionId")
    event_id: Optional[int] = Field(default=None, alias="eventId")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")
    type: Optional[str] = Field(default=None, alias="type")
    title: Optional[str] = Field(default=None, alias="title")
    message: Optional[str] = Field(default=None, alias="message")

    # Structured fields (if present)
    class_abbreviation: Optional[str] = Field(default=None, alias="classAbbreviation")
    driver_name: Optional[str] = Field(default=None, alias="driverName")
    vehicle: Optional[str] = Field(default=None, alias="marque")
    track_name: Optional[str] = Field(default=None, alias="trackName")
    date: Optional[str] = Field(default=None, alias="date")

    # Lap time: accept string or number; expose seconds
    lap_time: Optional[float] = Field(default=None, alias="lapTime")
    lap_time_str: Optional[str] = Field(default=None, alias="lapTimeString")
    lap_time_seconds: Optional[float] = Field(default=None, alias="lapTimeSeconds")

    @field_validator("lap_time", mode="before")
    @classmethod
    def _coerce_lap_time(cls, v: Any) -> Optional[float]:
        return _parse_lap_time_to_seconds(v)

    @model_validator(mode="after")
    def _ensure_seconds(self) -> "Announcement":
        if self.lap_time_seconds is None:
            if self.lap_time is not None:
                object.__setattr__(self, "lap_time_seconds", float(self.lap_time))
            elif self.lap_time_str:
                seconds = _parse_lap_time_to_seconds(self.lap_time_str)
                if seconds is not None:
                    object.__setattr__(self, "lap_time_seconds", seconds)
        return self


# ------------------------------------------------------------------------------
# Response Wrappers (normalize shapes like 'items', 'events', raw list)
# ------------------------------------------------------------------------------

class BasePage(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    count: Optional[int] = Field(default=None, alias="count")
    offset: Optional[int] = Field(default=None, alias="offset")
    total_count: Optional[int] = Field(default=None, alias="totalCount")
    next: Optional[str] = Field(default=None, alias="next")
    prev: Optional[str] = Field(default=None, alias="prev")


class EventsPage(BasePage):
    """
    Page wrapper for events. Accepts:
    - {"items": [ ...Event... ]}
    - {"events": [ ...Event... ]}
    - raw list [ ...Event... ]
    """
    items: List[Event] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Dict[str, Any]:
        if isinstance(data, list):
            return {"items": data}
        if isinstance(data, dict):
            for key in ("items", "events", "data"):
                maybe = data.get(key)
                if isinstance(maybe, list):
                    new = dict(data)
                    new["items"] = maybe
                    return new
            new = dict(data)
            new.setdefault("items", [])
            return new
        return {"items": []}


class AnnouncementsPage(BasePage):
    """
    Page wrapper for announcements. Accepts:
    - {"items": [ ...Announcement... ]}
    - {"announcements": [ ...Announcement... ]}
    - {"records": [ ...Announcement... ]}
    - raw list [ ...Announcement... ]
    """
    items: List[Announcement] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Dict[str, Any]:
        if isinstance(data, list):
            return {"items": data}
        if isinstance(data, dict):
            for key in ("items", "announcements", "records", "data"):
                maybe = data.get(key)
                if isinstance(maybe, list):
                    new = dict(data)
                    new["items"] = maybe
                    return new
            new = dict(data)
            new.setdefault("items", [])
            return new
        return {"items": []}


class SessionsPage(BasePage):
    """
    Wrapper for sessions when fetched in bulk (not common for this API).
    """
    items: List[Session] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Dict[str, Any]:
        if isinstance(data, list):
            return {"items": data}
        if isinstance(data, dict):
            for key in ("items", "sessions", "data"):
                maybe = data.get(key)
                if isinstance(maybe, list):
                    new = dict(data)
                    new["items"] = maybe
                    return new
            new = dict(data)
            new.setdefault("items", [])
            return new
        return {"items": []}


class OrganizationEvents(BaseModel):
    """
    Convenience: organization + its events (if endpoint returns both together).
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    organization: Optional[Organization] = Field(default=None, alias="organization")
    events: List[Event] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Dict[str, Any]:
        if isinstance(data, list):
            return {"events": data}
        if isinstance(data, dict):
            out: Dict[str, Any] = dict(data)
            for key in ("items", "events"):
                maybe = data.get(key)
                if isinstance(maybe, list):
                    out["events"] = maybe
                    break
            out.setdefault("events", [])
            return out
        return {"events": []}


__all__ = [
    "Country",
    "Location",
    "Organization",
    "Event",
    "Session",
    "Announcement",
    "BasePage",
    "EventsPage",
    "AnnouncementsPage",
    "SessionsPage",
    "OrganizationEvents",
]
