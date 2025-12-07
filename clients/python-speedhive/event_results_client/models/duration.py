from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Duration")


@_attrs_define
class Duration:
    """
    Attributes:
        standard_days (int | Unset):
        standard_hours (int | Unset):
        standard_minutes (int | Unset):
        standard_seconds (int | Unset):
        millis (int | Unset):
    """

    standard_days: int | Unset = UNSET
    standard_hours: int | Unset = UNSET
    standard_minutes: int | Unset = UNSET
    standard_seconds: int | Unset = UNSET
    millis: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        standard_days = self.standard_days

        standard_hours = self.standard_hours

        standard_minutes = self.standard_minutes

        standard_seconds = self.standard_seconds

        millis = self.millis

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if standard_days is not UNSET:
            field_dict["standardDays"] = standard_days
        if standard_hours is not UNSET:
            field_dict["standardHours"] = standard_hours
        if standard_minutes is not UNSET:
            field_dict["standardMinutes"] = standard_minutes
        if standard_seconds is not UNSET:
            field_dict["standardSeconds"] = standard_seconds
        if millis is not UNSET:
            field_dict["millis"] = millis

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        standard_days = d.pop("standardDays", UNSET)

        standard_hours = d.pop("standardHours", UNSET)

        standard_minutes = d.pop("standardMinutes", UNSET)

        standard_seconds = d.pop("standardSeconds", UNSET)

        millis = d.pop("millis", UNSET)

        duration = cls(
            standard_days=standard_days,
            standard_hours=standard_hours,
            standard_minutes=standard_minutes,
            standard_seconds=standard_seconds,
            millis=millis,
        )

        duration.additional_properties = d
        return duration

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
