from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.lap_position_status_item import LapPositionStatusItem
from ..types import UNSET, Unset

T = TypeVar("T", bound="LapPosition")


@_attrs_define
class LapPosition:
    """
    Attributes:
        position (int | Unset):
        start_number (str | Unset):
        in_leader_lap (bool | Unset):
        in_pit (bool | Unset):
        status (list[LapPositionStatusItem] | Unset):
    """

    position: int | Unset = UNSET
    start_number: str | Unset = UNSET
    in_leader_lap: bool | Unset = UNSET
    in_pit: bool | Unset = UNSET
    status: list[LapPositionStatusItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        position = self.position

        start_number = self.start_number

        in_leader_lap = self.in_leader_lap

        in_pit = self.in_pit

        status: list[str] | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = []
            for status_item_data in self.status:
                status_item = status_item_data.value
                status.append(status_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if position is not UNSET:
            field_dict["position"] = position
        if start_number is not UNSET:
            field_dict["startNumber"] = start_number
        if in_leader_lap is not UNSET:
            field_dict["inLeaderLap"] = in_leader_lap
        if in_pit is not UNSET:
            field_dict["inPit"] = in_pit
        if status is not UNSET:
            field_dict["status"] = status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        position = d.pop("position", UNSET)

        start_number = d.pop("startNumber", UNSET)

        in_leader_lap = d.pop("inLeaderLap", UNSET)

        in_pit = d.pop("inPit", UNSET)

        _status = d.pop("status", UNSET)
        status: list[LapPositionStatusItem] | Unset = UNSET
        if _status is not UNSET:
            status = []
            for status_item_data in _status:
                status_item = LapPositionStatusItem(status_item_data)

                status.append(status_item)

        lap_position = cls(
            position=position,
            start_number=start_number,
            in_leader_lap=in_leader_lap,
            in_pit=in_pit,
            status=status,
        )

        lap_position.additional_properties = d
        return lap_position

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
