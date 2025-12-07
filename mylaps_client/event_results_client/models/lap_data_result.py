from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.lap_info import LapInfo
    from ..models.lap_times_info import LapTimesInfo


T = TypeVar("T", bound="LapDataResult")


@_attrs_define
class LapDataResult:
    """
    Attributes:
        lap_data_info (LapInfo | Unset):
        laps (list[LapTimesInfo] | Unset):
    """

    lap_data_info: LapInfo | Unset = UNSET
    laps: list[LapTimesInfo] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        lap_data_info: dict[str, Any] | Unset = UNSET
        if not isinstance(self.lap_data_info, Unset):
            lap_data_info = self.lap_data_info.to_dict()

        laps: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.laps, Unset):
            laps = []
            for laps_item_data in self.laps:
                laps_item = laps_item_data.to_dict()
                laps.append(laps_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if lap_data_info is not UNSET:
            field_dict["lapDataInfo"] = lap_data_info
        if laps is not UNSET:
            field_dict["laps"] = laps

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lap_info import LapInfo
        from ..models.lap_times_info import LapTimesInfo

        d = dict(src_dict)
        _lap_data_info = d.pop("lapDataInfo", UNSET)
        lap_data_info: LapInfo | Unset
        if isinstance(_lap_data_info, Unset):
            lap_data_info = UNSET
        else:
            lap_data_info = LapInfo.from_dict(_lap_data_info)

        _laps = d.pop("laps", UNSET)
        laps: list[LapTimesInfo] | Unset = UNSET
        if _laps is not UNSET:
            laps = []
            for laps_item_data in _laps:
                laps_item = LapTimesInfo.from_dict(laps_item_data)

                laps.append(laps_item)

        lap_data_result = cls(
            lap_data_info=lap_data_info,
            laps=laps,
        )

        lap_data_result.additional_properties = d
        return lap_data_result

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
