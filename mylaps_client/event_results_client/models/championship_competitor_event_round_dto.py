from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ChampionshipCompetitorEventRoundDto")


@_attrs_define
class ChampionshipCompetitorEventRoundDto:
    """
    Attributes:
        round_id (int | Unset):
        points (float | Unset):
        position (str | Unset):
        is_dropped (bool | Unset):
    """

    round_id: int | Unset = UNSET
    points: float | Unset = UNSET
    position: str | Unset = UNSET
    is_dropped: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        round_id = self.round_id

        points = self.points

        position = self.position

        is_dropped = self.is_dropped

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if round_id is not UNSET:
            field_dict["roundId"] = round_id
        if points is not UNSET:
            field_dict["points"] = points
        if position is not UNSET:
            field_dict["position"] = position
        if is_dropped is not UNSET:
            field_dict["isDropped"] = is_dropped

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        round_id = d.pop("roundId", UNSET)

        points = d.pop("points", UNSET)

        position = d.pop("position", UNSET)

        is_dropped = d.pop("isDropped", UNSET)

        championship_competitor_event_round_dto = cls(
            round_id=round_id,
            points=points,
            position=position,
            is_dropped=is_dropped,
        )

        championship_competitor_event_round_dto.additional_properties = d
        return championship_competitor_event_round_dto

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
