from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.member import Member


T = TypeVar("T", bound="Chip")


@_attrs_define
class Chip:
    """The chip.

    Attributes:
        no (str | Unset):
        member (Member | Unset): The member.
    """

    no: str | Unset = UNSET
    member: Member | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        no = self.no

        member: dict[str, Any] | Unset = UNSET
        if not isinstance(self.member, Unset):
            member = self.member.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if no is not UNSET:
            field_dict["no"] = no
        if member is not UNSET:
            field_dict["member"] = member

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.member import Member

        d = dict(src_dict)
        no = d.pop("no", UNSET)

        _member = d.pop("member", UNSET)
        member: Member | Unset
        if isinstance(_member, Unset):
            member = UNSET
        else:
            member = Member.from_dict(_member)

        chip = cls(
            no=no,
            member=member,
        )

        chip.additional_properties = d
        return chip

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
