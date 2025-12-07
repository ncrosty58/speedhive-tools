from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.lap_times_lap import LapTimesLap


T = TypeVar("T", bound="LapTimes")


@_attrs_define
class LapTimes:
    """
    Attributes:
        session_id (int | Unset):
        laps (list[LapTimesLap] | Unset):
        session_ref (str | Unset):
        position (int | Unset):
    """

    session_id: int | Unset = UNSET
    laps: list[LapTimesLap] | Unset = UNSET
    session_ref: str | Unset = UNSET
    position: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        session_id = self.session_id

        laps: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.laps, Unset):
            laps = []
            for laps_item_data in self.laps:
                laps_item = laps_item_data.to_dict()
                laps.append(laps_item)

        session_ref = self.session_ref

        position = self.position

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if session_id is not UNSET:
            field_dict["sessionId"] = session_id
        if laps is not UNSET:
            field_dict["laps"] = laps
        if session_ref is not UNSET:
            field_dict["sessionRef"] = session_ref
        if position is not UNSET:
            field_dict["position"] = position

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lap_times_lap import LapTimesLap

        d = dict(src_dict)
        session_id = d.pop("sessionId", UNSET)

        _laps = d.pop("laps", UNSET)
        laps: list[LapTimesLap] | Unset = UNSET
        if _laps is not UNSET:
            laps = []
            for laps_item_data in _laps:
                laps_item = LapTimesLap.from_dict(laps_item_data)

                laps.append(laps_item)

        session_ref = d.pop("sessionRef", UNSET)

        position = d.pop("position", UNSET)

        lap_times = cls(
            session_id=session_id,
            laps=laps,
            session_ref=session_ref,
            position=position,
        )

        lap_times.additional_properties = d
        return lap_times

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
