from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="Session")


@_attrs_define
class Session:
    """
    Attributes:
        id (int | Unset):
        name (str | Unset):
        comment (str | Unset):
        event_id (int | Unset):
        type_ (str | Unset):
        start_time (datetime.datetime | Unset):
        group_name (str | Unset):
        is_merge (bool | Unset):
        result_status (str | Unset):
        participated (int | Unset):
        event_ref (str | Unset):
    """

    id: int | Unset = UNSET
    name: str | Unset = UNSET
    comment: str | Unset = UNSET
    event_id: int | Unset = UNSET
    type_: str | Unset = UNSET
    start_time: datetime.datetime | Unset = UNSET
    group_name: str | Unset = UNSET
    is_merge: bool | Unset = UNSET
    result_status: str | Unset = UNSET
    participated: int | Unset = UNSET
    event_ref: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        comment = self.comment

        event_id = self.event_id

        type_ = self.type_

        start_time: str | Unset = UNSET
        if not isinstance(self.start_time, Unset):
            start_time = self.start_time.isoformat()

        group_name = self.group_name

        is_merge = self.is_merge

        result_status = self.result_status

        participated = self.participated

        event_ref = self.event_ref

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if comment is not UNSET:
            field_dict["comment"] = comment
        if event_id is not UNSET:
            field_dict["eventId"] = event_id
        if type_ is not UNSET:
            field_dict["type"] = type_
        if start_time is not UNSET:
            field_dict["startTime"] = start_time
        if group_name is not UNSET:
            field_dict["groupName"] = group_name
        if is_merge is not UNSET:
            field_dict["isMerge"] = is_merge
        if result_status is not UNSET:
            field_dict["resultStatus"] = result_status
        if participated is not UNSET:
            field_dict["participated"] = participated
        if event_ref is not UNSET:
            field_dict["eventRef"] = event_ref

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        comment = d.pop("comment", UNSET)

        event_id = d.pop("eventId", UNSET)

        type_ = d.pop("type", UNSET)

        _start_time = d.pop("startTime", UNSET)
        start_time: datetime.datetime | Unset
        if isinstance(_start_time, Unset):
            start_time = UNSET
        else:
            start_time = isoparse(_start_time)

        group_name = d.pop("groupName", UNSET)

        is_merge = d.pop("isMerge", UNSET)

        result_status = d.pop("resultStatus", UNSET)

        participated = d.pop("participated", UNSET)

        event_ref = d.pop("eventRef", UNSET)

        session = cls(
            id=id,
            name=name,
            comment=comment,
            event_id=event_id,
            type_=type_,
            start_time=start_time,
            group_name=group_name,
            is_merge=is_merge,
            result_status=result_status,
            participated=participated,
            event_ref=event_ref,
        )

        session.additional_properties = d
        return session

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
