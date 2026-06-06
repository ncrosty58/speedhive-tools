from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ChipUsed")


@_attrs_define
class ChipUsed:
    """
    Attributes:
        chip_no (str | Unset):
        used (bool | Unset):
    """

    chip_no: str | Unset = UNSET
    used: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        chip_no = self.chip_no

        used = self.used

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if chip_no is not UNSET:
            field_dict["chipNo"] = chip_no
        if used is not UNSET:
            field_dict["used"] = used

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        chip_no = d.pop("chipNo", UNSET)

        used = d.pop("used", UNSET)

        chip_used = cls(
            chip_no=chip_no,
            used=used,
        )

        chip_used.additional_properties = d
        return chip_used

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
