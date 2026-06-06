from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.championship import Championship


T = TypeVar("T", bound="Championships")


@_attrs_define
class Championships:
    """
    Attributes:
        championships (list[Championship] | Unset):
    """

    championships: list[Championship] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        championships: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.championships, Unset):
            championships = []
            for championships_item_data in self.championships:
                championships_item = championships_item_data.to_dict()
                championships.append(championships_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if championships is not UNSET:
            field_dict["championships"] = championships

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.championship import Championship

        d = dict(src_dict)
        _championships = d.pop("championships", UNSET)
        championships: list[Championship] | Unset = UNSET
        if _championships is not UNSET:
            championships = []
            for championships_item_data in _championships:
                championships_item = Championship.from_dict(championships_item_data)

                championships.append(championships_item)

        championships = cls(
            championships=championships,
        )

        championships.additional_properties = d
        return championships

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
