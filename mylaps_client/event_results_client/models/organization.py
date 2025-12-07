from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.organization_sport import OrganizationSport
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.country import Country


T = TypeVar("T", bound="Organization")


@_attrs_define
class Organization:
    """
    Attributes:
        id (int | Unset):
        name (str | Unset):
        logo (str | Unset):
        url (str | Unset):
        city (str | Unset):
        country (Country | Unset):
        sport (OrganizationSport | Unset):
        ref (str | Unset):
    """

    id: int | Unset = UNSET
    name: str | Unset = UNSET
    logo: str | Unset = UNSET
    url: str | Unset = UNSET
    city: str | Unset = UNSET
    country: Country | Unset = UNSET
    sport: OrganizationSport | Unset = UNSET
    ref: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        logo = self.logo

        url = self.url

        city = self.city

        country: dict[str, Any] | Unset = UNSET
        if not isinstance(self.country, Unset):
            country = self.country.to_dict()

        sport: str | Unset = UNSET
        if not isinstance(self.sport, Unset):
            sport = self.sport.value

        ref = self.ref

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if logo is not UNSET:
            field_dict["logo"] = logo
        if url is not UNSET:
            field_dict["url"] = url
        if city is not UNSET:
            field_dict["city"] = city
        if country is not UNSET:
            field_dict["country"] = country
        if sport is not UNSET:
            field_dict["sport"] = sport
        if ref is not UNSET:
            field_dict["ref"] = ref

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.country import Country

        d = dict(src_dict)
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        logo = d.pop("logo", UNSET)

        url = d.pop("url", UNSET)

        city = d.pop("city", UNSET)

        _country = d.pop("country", UNSET)
        country: Country | Unset
        if isinstance(_country, Unset):
            country = UNSET
        else:
            country = Country.from_dict(_country)

        _sport = d.pop("sport", UNSET)
        sport: OrganizationSport | Unset
        if isinstance(_sport, Unset):
            sport = UNSET
        else:
            sport = OrganizationSport(_sport)

        ref = d.pop("ref", UNSET)

        organization = cls(
            id=id,
            name=name,
            logo=logo,
            url=url,
            city=city,
            country=country,
            sport=sport,
            ref=ref,
        )

        organization.additional_properties = d
        return organization

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
