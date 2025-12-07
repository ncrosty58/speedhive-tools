from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.championship_competitor_event_round_dto import ChampionshipCompetitorEventRoundDto


T = TypeVar("T", bound="ChampionshipCompetitorEventDto")


@_attrs_define
class ChampionshipCompetitorEventDto:
    """
    Attributes:
        event_id (int | Unset):
        points (float | Unset):
        position (str | Unset):
        is_dropped (bool | Unset):
        rounds (list[ChampionshipCompetitorEventRoundDto] | Unset):
    """

    event_id: int | Unset = UNSET
    points: float | Unset = UNSET
    position: str | Unset = UNSET
    is_dropped: bool | Unset = UNSET
    rounds: list[ChampionshipCompetitorEventRoundDto] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        event_id = self.event_id

        points = self.points

        position = self.position

        is_dropped = self.is_dropped

        rounds: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.rounds, Unset):
            rounds = []
            for rounds_item_data in self.rounds:
                rounds_item = rounds_item_data.to_dict()
                rounds.append(rounds_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if event_id is not UNSET:
            field_dict["eventId"] = event_id
        if points is not UNSET:
            field_dict["points"] = points
        if position is not UNSET:
            field_dict["position"] = position
        if is_dropped is not UNSET:
            field_dict["isDropped"] = is_dropped
        if rounds is not UNSET:
            field_dict["rounds"] = rounds

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.championship_competitor_event_round_dto import ChampionshipCompetitorEventRoundDto

        d = dict(src_dict)
        event_id = d.pop("eventId", UNSET)

        points = d.pop("points", UNSET)

        position = d.pop("position", UNSET)

        is_dropped = d.pop("isDropped", UNSET)

        _rounds = d.pop("rounds", UNSET)
        rounds: list[ChampionshipCompetitorEventRoundDto] | Unset = UNSET
        if _rounds is not UNSET:
            rounds = []
            for rounds_item_data in _rounds:
                rounds_item = ChampionshipCompetitorEventRoundDto.from_dict(rounds_item_data)

                rounds.append(rounds_item)

        championship_competitor_event_dto = cls(
            event_id=event_id,
            points=points,
            position=position,
            is_dropped=is_dropped,
            rounds=rounds,
        )

        championship_competitor_event_dto.additional_properties = d
        return championship_competitor_event_dto

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
