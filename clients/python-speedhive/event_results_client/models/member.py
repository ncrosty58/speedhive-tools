from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Member")


@_attrs_define
class Member:
    """The member.

    Attributes:
        id (int | Unset):
        ga_account (str | Unset):
        email (str | Unset):
        first_name (str | Unset):
        last_name (str | Unset):
        password (str | Unset):
        username (str | Unset):
        country (int | Unset):
        sport (int | Unset):
        show_additional (bool | Unset):
        organization_name (str | Unset):
        organization (bool | Unset):
    """

    id: int | Unset = UNSET
    ga_account: str | Unset = UNSET
    email: str | Unset = UNSET
    first_name: str | Unset = UNSET
    last_name: str | Unset = UNSET
    password: str | Unset = UNSET
    username: str | Unset = UNSET
    country: int | Unset = UNSET
    sport: int | Unset = UNSET
    show_additional: bool | Unset = UNSET
    organization_name: str | Unset = UNSET
    organization: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        ga_account = self.ga_account

        email = self.email

        first_name = self.first_name

        last_name = self.last_name

        password = self.password

        username = self.username

        country = self.country

        sport = self.sport

        show_additional = self.show_additional

        organization_name = self.organization_name

        organization = self.organization

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if ga_account is not UNSET:
            field_dict["gaAccount"] = ga_account
        if email is not UNSET:
            field_dict["email"] = email
        if first_name is not UNSET:
            field_dict["firstName"] = first_name
        if last_name is not UNSET:
            field_dict["lastName"] = last_name
        if password is not UNSET:
            field_dict["password"] = password
        if username is not UNSET:
            field_dict["username"] = username
        if country is not UNSET:
            field_dict["country"] = country
        if sport is not UNSET:
            field_dict["sport"] = sport
        if show_additional is not UNSET:
            field_dict["showAdditional"] = show_additional
        if organization_name is not UNSET:
            field_dict["organizationName"] = organization_name
        if organization is not UNSET:
            field_dict["organization"] = organization

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        ga_account = d.pop("gaAccount", UNSET)

        email = d.pop("email", UNSET)

        first_name = d.pop("firstName", UNSET)

        last_name = d.pop("lastName", UNSET)

        password = d.pop("password", UNSET)

        username = d.pop("username", UNSET)

        country = d.pop("country", UNSET)

        sport = d.pop("sport", UNSET)

        show_additional = d.pop("showAdditional", UNSET)

        organization_name = d.pop("organizationName", UNSET)

        organization = d.pop("organization", UNSET)

        member = cls(
            id=id,
            ga_account=ga_account,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            username=username,
            country=country,
            sport=sport,
            show_additional=show_additional,
            organization_name=organization_name,
            organization=organization,
        )

        member.additional_properties = d
        return member

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
