from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.event_sport import EventSport
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.event_sessions_and_groups import EventSessionsAndGroups
    from ..models.location import Location
    from ..models.organization import Organization
    from ..models.upload_software import UploadSoftware


T = TypeVar("T", bound="Event")


@_attrs_define
class Event:
    """
    Attributes:
        id (int | Unset):
        name (str | Unset):
        organization (Organization | Unset):
        sport (EventSport | Unset):
        start_date (datetime.date | Unset):
        location (Location | Unset):
        upload_software (UploadSoftware | Unset):
        updated_at (datetime.datetime | Unset):
        sessions (EventSessionsAndGroups | Unset):
    """

    id: int | Unset = UNSET
    name: str | Unset = UNSET
    organization: Organization | Unset = UNSET
    sport: EventSport | Unset = UNSET
    start_date: datetime.date | Unset = UNSET
    location: Location | Unset = UNSET
    upload_software: UploadSoftware | Unset = UNSET
    updated_at: datetime.datetime | Unset = UNSET
    sessions: EventSessionsAndGroups | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        organization: dict[str, Any] | Unset = UNSET
        if not isinstance(self.organization, Unset):
            organization = self.organization.to_dict()

        sport: str | Unset = UNSET
        if not isinstance(self.sport, Unset):
            sport = self.sport.value

        start_date: str | Unset = UNSET
        if not isinstance(self.start_date, Unset):
            start_date = self.start_date.isoformat()

        location: dict[str, Any] | Unset = UNSET
        if not isinstance(self.location, Unset):
            location = self.location.to_dict()

        upload_software: dict[str, Any] | Unset = UNSET
        if not isinstance(self.upload_software, Unset):
            upload_software = self.upload_software.to_dict()

        updated_at: str | Unset = UNSET
        if not isinstance(self.updated_at, Unset):
            updated_at = self.updated_at.isoformat()

        sessions: dict[str, Any] | Unset = UNSET
        if not isinstance(self.sessions, Unset):
            sessions = self.sessions.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if organization is not UNSET:
            field_dict["organization"] = organization
        if sport is not UNSET:
            field_dict["sport"] = sport
        if start_date is not UNSET:
            field_dict["startDate"] = start_date
        if location is not UNSET:
            field_dict["location"] = location
        if upload_software is not UNSET:
            field_dict["uploadSoftware"] = upload_software
        if updated_at is not UNSET:
            field_dict["updatedAt"] = updated_at
        if sessions is not UNSET:
            field_dict["sessions"] = sessions

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.event_sessions_and_groups import EventSessionsAndGroups
        from ..models.location import Location
        from ..models.organization import Organization
        from ..models.upload_software import UploadSoftware

        d = dict(src_dict)
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        _organization = d.pop("organization", UNSET)
        organization: Organization | Unset
        if isinstance(_organization, Unset):
            organization = UNSET
        else:
            organization = Organization.from_dict(_organization)

        _sport = d.pop("sport", UNSET)
        sport: EventSport | Unset
        if isinstance(_sport, Unset):
            sport = UNSET
        else:
            sport = EventSport(_sport)

        _start_date = d.pop("startDate", UNSET)
        start_date: datetime.date | Unset
        if isinstance(_start_date, Unset):
            start_date = UNSET
        else:
            start_date = isoparse(_start_date).date()

        _location = d.pop("location", UNSET)
        location: Location | Unset
        if isinstance(_location, Unset):
            location = UNSET
        else:
            location = Location.from_dict(_location)

        _upload_software = d.pop("uploadSoftware", UNSET)
        upload_software: UploadSoftware | Unset
        if isinstance(_upload_software, Unset):
            upload_software = UNSET
        else:
            upload_software = UploadSoftware.from_dict(_upload_software)

        _updated_at = d.pop("updatedAt", UNSET)
        updated_at: datetime.datetime | Unset
        if isinstance(_updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = isoparse(_updated_at)

        _sessions = d.pop("sessions", UNSET)
        sessions: EventSessionsAndGroups | Unset
        if isinstance(_sessions, Unset):
            sessions = UNSET
        else:
            sessions = EventSessionsAndGroups.from_dict(_sessions)

        event = cls(
            id=id,
            name=name,
            organization=organization,
            sport=sport,
            start_date=start_date,
            location=location,
            upload_software=upload_software,
            updated_at=updated_at,
            sessions=sessions,
        )

        event.additional_properties = d
        return event

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
