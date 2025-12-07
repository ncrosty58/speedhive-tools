from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ChampionshipModel")


@_attrs_define
class ChampionshipModel:
    """
    Attributes:
        id (int | Unset):
        organization (int | Unset):
        name (str | Unset):
        season (str | Unset):
        xml (str | Unset):
    """

    id: int | Unset = UNSET
    organization: int | Unset = UNSET
    name: str | Unset = UNSET
    season: str | Unset = UNSET
    xml: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        organization = self.organization

        name = self.name

        season = self.season

        xml = self.xml

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if organization is not UNSET:
            field_dict["organization"] = organization
        if name is not UNSET:
            field_dict["name"] = name
        if season is not UNSET:
            field_dict["season"] = season
        if xml is not UNSET:
            field_dict["xml"] = xml

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        organization = d.pop("organization", UNSET)

        name = d.pop("name", UNSET)

        season = d.pop("season", UNSET)

        xml = d.pop("xml", UNSET)

        championship_model = cls(
            id=id,
            organization=organization,
            name=name,
            season=season,
            xml=xml,
        )

        championship_model.additional_properties = d
        return championship_model

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
