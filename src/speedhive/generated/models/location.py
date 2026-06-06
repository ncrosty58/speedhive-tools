from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.country import Country


T = TypeVar("T", bound="Location")


@_attrs_define
class Location:
    """
    Attributes:
        length_label (str | Unset):
        name (str | Unset):
        length (float | Unset):
        id (int | Unset):
        country (Country | Unset):
        length_unit (str | Unset):
    """

    length_label: str | Unset = UNSET
    name: str | Unset = UNSET
    length: float | Unset = UNSET
    id: int | Unset = UNSET
    country: Country | Unset = UNSET
    length_unit: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        length_label = self.length_label

        name = self.name

        length = self.length

        id = self.id

        country: dict[str, Any] | Unset = UNSET
        if not isinstance(self.country, Unset):
            country = self.country.to_dict()

        length_unit = self.length_unit

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if length_label is not UNSET:
            field_dict["lengthLabel"] = length_label
        if name is not UNSET:
            field_dict["name"] = name
        if length is not UNSET:
            field_dict["length"] = length
        if id is not UNSET:
            field_dict["id"] = id
        if country is not UNSET:
            field_dict["country"] = country
        if length_unit is not UNSET:
            field_dict["lengthUnit"] = length_unit

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.country import Country

        d = dict(src_dict)
        length_label = d.pop("lengthLabel", UNSET)

        name = d.pop("name", UNSET)

        length = d.pop("length", UNSET)

        id = d.pop("id", UNSET)

        _country = d.pop("country", UNSET)
        country: Country | Unset
        if isinstance(_country, Unset):
            country = UNSET
        else:
            country = Country.from_dict(_country)

        length_unit = d.pop("lengthUnit", UNSET)

        location = cls(
            length_label=length_label,
            name=name,
            length=length,
            id=id,
            country=country,
            length_unit=length_unit,
        )

        location.additional_properties = d
        return location

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
