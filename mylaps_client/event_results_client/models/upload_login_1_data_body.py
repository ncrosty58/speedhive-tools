from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="UploadLogin1DataBody")


@_attrs_define
class UploadLogin1DataBody:
    """
    Attributes:
        login_name (str):
        login_pass (str):
    """

    login_name: str
    login_pass: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        login_name = self.login_name

        login_pass = self.login_pass

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "loginName": login_name,
                "loginPass": login_pass,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        login_name = d.pop("loginName")

        login_pass = d.pop("loginPass")

        upload_login_1_data_body = cls(
            login_name=login_name,
            login_pass=login_pass,
        )

        upload_login_1_data_body.additional_properties = d
        return upload_login_1_data_body

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
