from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.orbit_validation_error import OrbitValidationError


T = TypeVar("T", bound="OrbitUploadResult")


@_attrs_define
class OrbitUploadResult:
    """
    Attributes:
        is_success (bool | Unset):
        event_url (str | Unset):
        validation_errors (list[OrbitValidationError] | Unset):
    """

    is_success: bool | Unset = UNSET
    event_url: str | Unset = UNSET
    validation_errors: list[OrbitValidationError] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        is_success = self.is_success

        event_url = self.event_url

        validation_errors: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.validation_errors, Unset):
            validation_errors = []
            for validation_errors_item_data in self.validation_errors:
                validation_errors_item = validation_errors_item_data.to_dict()
                validation_errors.append(validation_errors_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if is_success is not UNSET:
            field_dict["isSuccess"] = is_success
        if event_url is not UNSET:
            field_dict["eventUrl"] = event_url
        if validation_errors is not UNSET:
            field_dict["validationErrors"] = validation_errors

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.orbit_validation_error import OrbitValidationError

        d = dict(src_dict)
        is_success = d.pop("isSuccess", UNSET)

        event_url = d.pop("eventUrl", UNSET)

        _validation_errors = d.pop("validationErrors", UNSET)
        validation_errors: list[OrbitValidationError] | Unset = UNSET
        if _validation_errors is not UNSET:
            validation_errors = []
            for validation_errors_item_data in _validation_errors:
                validation_errors_item = OrbitValidationError.from_dict(validation_errors_item_data)

                validation_errors.append(validation_errors_item)

        orbit_upload_result = cls(
            is_success=is_success,
            event_url=event_url,
            validation_errors=validation_errors,
        )

        orbit_upload_result.additional_properties = d
        return orbit_upload_result

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
