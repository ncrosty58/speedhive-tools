from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.lap_info_classification_type_string import LapInfoClassificationTypeString
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.participant_info import ParticipantInfo


T = TypeVar("T", bound="LapInfo")


@_attrs_define
class LapInfo:
    """
    Attributes:
        participant_info (ParticipantInfo | Unset):
        lap_count (int | Unset):
        all_laps_have_field_pos (bool | Unset):
        first_lap_nr (int | Unset):
        laps_driven (int | Unset):
        classification_type (int | Unset):
        classification_type_string (LapInfoClassificationTypeString | Unset):
        session_id (int | Unset):
    """

    participant_info: ParticipantInfo | Unset = UNSET
    lap_count: int | Unset = UNSET
    all_laps_have_field_pos: bool | Unset = UNSET
    first_lap_nr: int | Unset = UNSET
    laps_driven: int | Unset = UNSET
    classification_type: int | Unset = UNSET
    classification_type_string: LapInfoClassificationTypeString | Unset = UNSET
    session_id: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        participant_info: dict[str, Any] | Unset = UNSET
        if not isinstance(self.participant_info, Unset):
            participant_info = self.participant_info.to_dict()

        lap_count = self.lap_count

        all_laps_have_field_pos = self.all_laps_have_field_pos

        first_lap_nr = self.first_lap_nr

        laps_driven = self.laps_driven

        classification_type = self.classification_type

        classification_type_string: str | Unset = UNSET
        if not isinstance(self.classification_type_string, Unset):
            classification_type_string = self.classification_type_string.value

        session_id = self.session_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if participant_info is not UNSET:
            field_dict["participantInfo"] = participant_info
        if lap_count is not UNSET:
            field_dict["lapCount"] = lap_count
        if all_laps_have_field_pos is not UNSET:
            field_dict["allLapsHaveFieldPos"] = all_laps_have_field_pos
        if first_lap_nr is not UNSET:
            field_dict["firstLapNr"] = first_lap_nr
        if laps_driven is not UNSET:
            field_dict["lapsDriven"] = laps_driven
        if classification_type is not UNSET:
            field_dict["classificationType"] = classification_type
        if classification_type_string is not UNSET:
            field_dict["classificationTypeString"] = classification_type_string
        if session_id is not UNSET:
            field_dict["sessionId"] = session_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.participant_info import ParticipantInfo

        d = dict(src_dict)
        _participant_info = d.pop("participantInfo", UNSET)
        participant_info: ParticipantInfo | Unset
        if isinstance(_participant_info, Unset):
            participant_info = UNSET
        else:
            participant_info = ParticipantInfo.from_dict(_participant_info)

        lap_count = d.pop("lapCount", UNSET)

        all_laps_have_field_pos = d.pop("allLapsHaveFieldPos", UNSET)

        first_lap_nr = d.pop("firstLapNr", UNSET)

        laps_driven = d.pop("lapsDriven", UNSET)

        classification_type = d.pop("classificationType", UNSET)

        _classification_type_string = d.pop("classificationTypeString", UNSET)
        classification_type_string: LapInfoClassificationTypeString | Unset
        if isinstance(_classification_type_string, Unset):
            classification_type_string = UNSET
        else:
            classification_type_string = LapInfoClassificationTypeString(_classification_type_string)

        session_id = d.pop("sessionId", UNSET)

        lap_info = cls(
            participant_info=participant_info,
            lap_count=lap_count,
            all_laps_have_field_pos=all_laps_have_field_pos,
            first_lap_nr=first_lap_nr,
            laps_driven=laps_driven,
            classification_type=classification_type,
            classification_type_string=classification_type_string,
            session_id=session_id,
        )

        lap_info.additional_properties = d
        return lap_info

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
