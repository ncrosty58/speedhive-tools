from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.group import Group
    from ..models.session import Session


T = TypeVar("T", bound="EventSessionsAndGroups")


@_attrs_define
class EventSessionsAndGroups:
    """
    Attributes:
        sessions (list[Session] | Unset):
        groups (list[Group] | Unset):
    """

    sessions: list[Session] | Unset = UNSET
    groups: list[Group] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        sessions: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.sessions, Unset):
            sessions = []
            for sessions_item_data in self.sessions:
                sessions_item = sessions_item_data.to_dict()
                sessions.append(sessions_item)

        groups: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.groups, Unset):
            groups = []
            for groups_item_data in self.groups:
                groups_item = groups_item_data.to_dict()
                groups.append(groups_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if sessions is not UNSET:
            field_dict["sessions"] = sessions
        if groups is not UNSET:
            field_dict["groups"] = groups

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.group import Group
        from ..models.session import Session

        d = dict(src_dict)
        _sessions = d.pop("sessions", UNSET)
        sessions: list[Session] | Unset = UNSET
        if _sessions is not UNSET:
            sessions = []
            for sessions_item_data in _sessions:
                sessions_item = Session.from_dict(sessions_item_data)

                sessions.append(sessions_item)

        _groups = d.pop("groups", UNSET)
        groups: list[Group] | Unset = UNSET
        if _groups is not UNSET:
            groups = []
            for groups_item_data in _groups:
                groups_item = Group.from_dict(groups_item_data)

                groups.append(groups_item)

        event_sessions_and_groups = cls(
            sessions=sessions,
            groups=groups,
        )

        event_sessions_and_groups.additional_properties = d
        return event_sessions_and_groups

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
