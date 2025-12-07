from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ParticipantInfo")


@_attrs_define
class ParticipantInfo:
    """
    Attributes:
        name (str | Unset):
        class_ (str | Unset):
        transponder (str | Unset):
        user_id (str | Unset):
        start_nr (str | Unset):
        start_pos (int | Unset):
        field_finish_pos (int | Unset):
        class_finish_pos (int | Unset):
    """

    name: str | Unset = UNSET
    class_: str | Unset = UNSET
    transponder: str | Unset = UNSET
    user_id: str | Unset = UNSET
    start_nr: str | Unset = UNSET
    start_pos: int | Unset = UNSET
    field_finish_pos: int | Unset = UNSET
    class_finish_pos: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        class_ = self.class_

        transponder = self.transponder

        user_id = self.user_id

        start_nr = self.start_nr

        start_pos = self.start_pos

        field_finish_pos = self.field_finish_pos

        class_finish_pos = self.class_finish_pos

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if class_ is not UNSET:
            field_dict["class"] = class_
        if transponder is not UNSET:
            field_dict["transponder"] = transponder
        if user_id is not UNSET:
            field_dict["userId"] = user_id
        if start_nr is not UNSET:
            field_dict["startNr"] = start_nr
        if start_pos is not UNSET:
            field_dict["startPos"] = start_pos
        if field_finish_pos is not UNSET:
            field_dict["fieldFinishPos"] = field_finish_pos
        if class_finish_pos is not UNSET:
            field_dict["classFinishPos"] = class_finish_pos

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name", UNSET)

        class_ = d.pop("class", UNSET)

        transponder = d.pop("transponder", UNSET)

        user_id = d.pop("userId", UNSET)

        start_nr = d.pop("startNr", UNSET)

        start_pos = d.pop("startPos", UNSET)

        field_finish_pos = d.pop("fieldFinishPos", UNSET)

        class_finish_pos = d.pop("classFinishPos", UNSET)

        participant_info = cls(
            name=name,
            class_=class_,
            transponder=transponder,
            user_id=user_id,
            start_nr=start_nr,
            start_pos=start_pos,
            field_finish_pos=field_finish_pos,
            class_finish_pos=class_finish_pos,
        )

        participant_info.additional_properties = d
        return participant_info

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
