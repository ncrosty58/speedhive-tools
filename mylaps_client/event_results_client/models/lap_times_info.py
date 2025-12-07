from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.lap_times_info_status_item import LapTimesInfoStatusItem
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.lap_comparison import LapComparison


T = TypeVar("T", bound="LapTimesInfo")


@_attrs_define
class LapTimesInfo:
    """
    Attributes:
        lap_nr (int | Unset):
        time_of_day (datetime.datetime | Unset):
        lap_time (str | Unset):
        diff_with_last_lap (str | Unset):
        diff_with_best_lap (str | Unset):
        speed (float | Unset):
        section_times (list[str] | Unset):
        in_pit (bool | Unset):
        status (list[LapTimesInfoStatusItem] | Unset):
        field_comparison (LapComparison | Unset):
    """

    lap_nr: int | Unset = UNSET
    time_of_day: datetime.datetime | Unset = UNSET
    lap_time: str | Unset = UNSET
    diff_with_last_lap: str | Unset = UNSET
    diff_with_best_lap: str | Unset = UNSET
    speed: float | Unset = UNSET
    section_times: list[str] | Unset = UNSET
    in_pit: bool | Unset = UNSET
    status: list[LapTimesInfoStatusItem] | Unset = UNSET
    field_comparison: LapComparison | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        lap_nr = self.lap_nr

        time_of_day: str | Unset = UNSET
        if not isinstance(self.time_of_day, Unset):
            time_of_day = self.time_of_day.isoformat()

        lap_time = self.lap_time

        diff_with_last_lap = self.diff_with_last_lap

        diff_with_best_lap = self.diff_with_best_lap

        speed = self.speed

        section_times: list[str] | Unset = UNSET
        if not isinstance(self.section_times, Unset):
            section_times = self.section_times

        in_pit = self.in_pit

        status: list[str] | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = []
            for status_item_data in self.status:
                status_item = status_item_data.value
                status.append(status_item)

        field_comparison: dict[str, Any] | Unset = UNSET
        if not isinstance(self.field_comparison, Unset):
            field_comparison = self.field_comparison.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if lap_nr is not UNSET:
            field_dict["lapNr"] = lap_nr
        if time_of_day is not UNSET:
            field_dict["timeOfDay"] = time_of_day
        if lap_time is not UNSET:
            field_dict["lapTime"] = lap_time
        if diff_with_last_lap is not UNSET:
            field_dict["diffWithLastLap"] = diff_with_last_lap
        if diff_with_best_lap is not UNSET:
            field_dict["diffWithBestLap"] = diff_with_best_lap
        if speed is not UNSET:
            field_dict["speed"] = speed
        if section_times is not UNSET:
            field_dict["sectionTimes"] = section_times
        if in_pit is not UNSET:
            field_dict["inPit"] = in_pit
        if status is not UNSET:
            field_dict["status"] = status
        if field_comparison is not UNSET:
            field_dict["fieldComparison"] = field_comparison

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lap_comparison import LapComparison

        d = dict(src_dict)
        lap_nr = d.pop("lapNr", UNSET)

        _time_of_day = d.pop("timeOfDay", UNSET)
        time_of_day: datetime.datetime | Unset
        if isinstance(_time_of_day, Unset):
            time_of_day = UNSET
        else:
            time_of_day = isoparse(_time_of_day)

        lap_time = d.pop("lapTime", UNSET)

        diff_with_last_lap = d.pop("diffWithLastLap", UNSET)

        diff_with_best_lap = d.pop("diffWithBestLap", UNSET)

        speed = d.pop("speed", UNSET)

        section_times = cast(list[str], d.pop("sectionTimes", UNSET))

        in_pit = d.pop("inPit", UNSET)

        _status = d.pop("status", UNSET)
        status: list[LapTimesInfoStatusItem] | Unset = UNSET
        if _status is not UNSET:
            status = []
            for status_item_data in _status:
                status_item = LapTimesInfoStatusItem(status_item_data)

                status.append(status_item)

        _field_comparison = d.pop("fieldComparison", UNSET)
        field_comparison: LapComparison | Unset
        if isinstance(_field_comparison, Unset):
            field_comparison = UNSET
        else:
            field_comparison = LapComparison.from_dict(_field_comparison)

        lap_times_info = cls(
            lap_nr=lap_nr,
            time_of_day=time_of_day,
            lap_time=lap_time,
            diff_with_last_lap=diff_with_last_lap,
            diff_with_best_lap=diff_with_best_lap,
            speed=speed,
            section_times=section_times,
            in_pit=in_pit,
            status=status,
            field_comparison=field_comparison,
        )

        lap_times_info.additional_properties = d
        return lap_times_info

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
