from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.lap_times_lap_status_item import LapTimesLapStatusItem
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.duration import Duration


T = TypeVar("T", bound="LapTimesLap")


@_attrs_define
class LapTimesLap:
    """
    Attributes:
        lap (int | Unset):
        lead_lap (int | Unset):
        time_of_day (Duration | Unset):
        lap_time (Duration | Unset):
        difference_with_last_lap (Duration | Unset):
        difference_with_best_lap (Duration | Unset):
        speed (float | Unset):
        section_times (list[Duration] | Unset):
        in_pit (bool | Unset):
        status (list[LapTimesLapStatusItem] | Unset):
    """

    lap: int | Unset = UNSET
    lead_lap: int | Unset = UNSET
    time_of_day: Duration | Unset = UNSET
    lap_time: Duration | Unset = UNSET
    difference_with_last_lap: Duration | Unset = UNSET
    difference_with_best_lap: Duration | Unset = UNSET
    speed: float | Unset = UNSET
    section_times: list[Duration] | Unset = UNSET
    in_pit: bool | Unset = UNSET
    status: list[LapTimesLapStatusItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        lap = self.lap

        lead_lap = self.lead_lap

        time_of_day: dict[str, Any] | Unset = UNSET
        if not isinstance(self.time_of_day, Unset):
            time_of_day = self.time_of_day.to_dict()

        lap_time: dict[str, Any] | Unset = UNSET
        if not isinstance(self.lap_time, Unset):
            lap_time = self.lap_time.to_dict()

        difference_with_last_lap: dict[str, Any] | Unset = UNSET
        if not isinstance(self.difference_with_last_lap, Unset):
            difference_with_last_lap = self.difference_with_last_lap.to_dict()

        difference_with_best_lap: dict[str, Any] | Unset = UNSET
        if not isinstance(self.difference_with_best_lap, Unset):
            difference_with_best_lap = self.difference_with_best_lap.to_dict()

        speed = self.speed

        section_times: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.section_times, Unset):
            section_times = []
            for section_times_item_data in self.section_times:
                section_times_item = section_times_item_data.to_dict()
                section_times.append(section_times_item)

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
        if lap is not UNSET:
            field_dict["lap"] = lap
        if lead_lap is not UNSET:
            field_dict["leadLap"] = lead_lap
        if time_of_day is not UNSET:
            field_dict["timeOfDay"] = time_of_day
        if lap_time is not UNSET:
            field_dict["lapTime"] = lap_time
        if difference_with_last_lap is not UNSET:
            field_dict["differenceWithLastLap"] = difference_with_last_lap
        if difference_with_best_lap is not UNSET:
            field_dict["differenceWithBestLap"] = difference_with_best_lap
        if speed is not UNSET:
            field_dict["speed"] = speed
        if section_times is not UNSET:
            field_dict["sectionTimes"] = section_times
        if in_pit is not UNSET:
            field_dict["inPit"] = in_pit
        if status is not UNSET:
            field_dict["status"] = status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.duration import Duration

        d = dict(src_dict)
        lap = d.pop("lap", UNSET)

        lead_lap = d.pop("leadLap", UNSET)

        _time_of_day = d.pop("timeOfDay", UNSET)
        time_of_day: Duration | Unset
        if isinstance(_time_of_day, Unset):
            time_of_day = UNSET
        else:
            time_of_day = Duration.from_dict(_time_of_day)

        _lap_time = d.pop("lapTime", UNSET)
        lap_time: Duration | Unset
        if isinstance(_lap_time, Unset):
            lap_time = UNSET
        else:
            lap_time = Duration.from_dict(_lap_time)

        _difference_with_last_lap = d.pop("differenceWithLastLap", UNSET)
        difference_with_last_lap: Duration | Unset
        if isinstance(_difference_with_last_lap, Unset):
            difference_with_last_lap = UNSET
        else:
            difference_with_last_lap = Duration.from_dict(_difference_with_last_lap)

        _difference_with_best_lap = d.pop("differenceWithBestLap", UNSET)
        difference_with_best_lap: Duration | Unset
        if isinstance(_difference_with_best_lap, Unset):
            difference_with_best_lap = UNSET
        else:
            difference_with_best_lap = Duration.from_dict(_difference_with_best_lap)

        speed = d.pop("speed", UNSET)

        _section_times = d.pop("sectionTimes", UNSET)
        section_times: list[Duration] | Unset = UNSET
        if _section_times is not UNSET:
            section_times = []
            for section_times_item_data in _section_times:
                section_times_item = Duration.from_dict(section_times_item_data)

                section_times.append(section_times_item)

        in_pit = d.pop("inPit", UNSET)

        _status = d.pop("status", UNSET)
        status: list[LapTimesLapStatusItem] | Unset = UNSET
        if _status is not UNSET:
            status = []
            for status_item_data in _status:
                status_item = LapTimesLapStatusItem(status_item_data)

                status.append(status_item)

        lap_times_lap = cls(
            lap=lap,
            lead_lap=lead_lap,
            time_of_day=time_of_day,
            lap_time=lap_time,
            difference_with_last_lap=difference_with_last_lap,
            difference_with_best_lap=difference_with_best_lap,
            speed=speed,
            section_times=section_times,
            in_pit=in_pit,
            status=status,
        )

        lap_times_lap.additional_properties = d
        return lap_times_lap

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
