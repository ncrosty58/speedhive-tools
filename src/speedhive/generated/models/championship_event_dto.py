from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.championship_event_round_dto import ChampionshipEventRoundDto


T = TypeVar("T", bound="ChampionshipEventDto")


@_attrs_define
class ChampionshipEventDto:
    """
    Attributes:
        id (int | Unset):
        name (str | Unset):
        date (str | Unset):
        rounds (list[ChampionshipEventRoundDto] | Unset):
    """

    id: int | Unset = UNSET
    name: str | Unset = UNSET
    date: str | Unset = UNSET
    rounds: list[ChampionshipEventRoundDto] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        date = self.date

        rounds: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.rounds, Unset):
            rounds = []
            for rounds_item_data in self.rounds:
                rounds_item = rounds_item_data.to_dict()
                rounds.append(rounds_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if date is not UNSET:
            field_dict["date"] = date
        if rounds is not UNSET:
            field_dict["rounds"] = rounds

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.championship_event_round_dto import ChampionshipEventRoundDto

        d = dict(src_dict)
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        date = d.pop("date", UNSET)

        _rounds = d.pop("rounds", UNSET)
        rounds: list[ChampionshipEventRoundDto] | Unset = UNSET
        if _rounds is not UNSET:
            rounds = []
            for rounds_item_data in _rounds:
                rounds_item = ChampionshipEventRoundDto.from_dict(rounds_item_data)

                rounds.append(rounds_item)

        championship_event_dto = cls(
            id=id,
            name=name,
            date=date,
            rounds=rounds,
        )

        championship_event_dto.additional_properties = d
        return championship_event_dto

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
