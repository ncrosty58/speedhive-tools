from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.session import Session


T = TypeVar("T", bound="Group")


@_attrs_define
class Group:
    """
    Attributes:
        id (int | Unset):
        name (str | Unset):
        date (datetime.date | Unset):
        sub_groups (list[Group] | Unset):
        sessions (list[Session] | Unset):
    """

    id: int | Unset = UNSET
    name: str | Unset = UNSET
    date: datetime.date | Unset = UNSET
    sub_groups: list[Group] | Unset = UNSET
    sessions: list[Session] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        date: str | Unset = UNSET
        if not isinstance(self.date, Unset):
            date = self.date.isoformat()

        sub_groups: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.sub_groups, Unset):
            sub_groups = []
            for sub_groups_item_data in self.sub_groups:
                sub_groups_item = sub_groups_item_data.to_dict()
                sub_groups.append(sub_groups_item)

        sessions: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.sessions, Unset):
            sessions = []
            for sessions_item_data in self.sessions:
                sessions_item = sessions_item_data.to_dict()
                sessions.append(sessions_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if date is not UNSET:
            field_dict["date"] = date
        if sub_groups is not UNSET:
            field_dict["subGroups"] = sub_groups
        if sessions is not UNSET:
            field_dict["sessions"] = sessions

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.session import Session

        d = dict(src_dict)
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        _date = d.pop("date", UNSET)
        date: datetime.date | Unset
        if isinstance(_date, Unset):
            date = UNSET
        else:
            date = isoparse(_date).date()

        _sub_groups = d.pop("subGroups", UNSET)
        sub_groups: list[Group] | Unset = UNSET
        if _sub_groups is not UNSET:
            sub_groups = []
            for sub_groups_item_data in _sub_groups:
                sub_groups_item = Group.from_dict(sub_groups_item_data)

                sub_groups.append(sub_groups_item)

        _sessions = d.pop("sessions", UNSET)
        sessions: list[Session] | Unset = UNSET
        if _sessions is not UNSET:
            sessions = []
            for sessions_item_data in _sessions:
                sessions_item = Session.from_dict(sessions_item_data)

                sessions.append(sessions_item)

        group = cls(
            id=id,
            name=name,
            date=date,
            sub_groups=sub_groups,
            sessions=sessions,
        )

        group.additional_properties = d
        return group

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
