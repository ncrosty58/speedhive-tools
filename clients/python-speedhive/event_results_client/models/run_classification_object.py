from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.run_classification_object_type import RunClassificationObjectType
from ..types import UNSET, Unset

T = TypeVar("T", bound="RunClassificationObject")


@_attrs_define
class RunClassificationObject:
    """
    Attributes:
        classes (list[str] | Unset):
        type_ (RunClassificationObjectType | Unset):
        rows (list[Any] | Unset):
    """

    classes: list[str] | Unset = UNSET
    type_: RunClassificationObjectType | Unset = UNSET
    rows: list[Any] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        classes: list[str] | Unset = UNSET
        if not isinstance(self.classes, Unset):
            classes = self.classes

        type_: str | Unset = UNSET
        if not isinstance(self.type_, Unset):
            type_ = self.type_.value

        rows: list[Any] | Unset = UNSET
        if not isinstance(self.rows, Unset):
            rows = self.rows

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if classes is not UNSET:
            field_dict["classes"] = classes
        if type_ is not UNSET:
            field_dict["type"] = type_
        if rows is not UNSET:
            field_dict["rows"] = rows

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        classes = cast(list[str], d.pop("classes", UNSET))

        _type_ = d.pop("type", UNSET)
        type_: RunClassificationObjectType | Unset
        if isinstance(_type_, Unset):
            type_ = UNSET
        else:
            type_ = RunClassificationObjectType(_type_)

        rows = cast(list[Any], d.pop("rows", UNSET))

        run_classification_object = cls(
            classes=classes,
            type_=type_,
            rows=rows,
        )

        run_classification_object.additional_properties = d
        return run_classification_object

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
