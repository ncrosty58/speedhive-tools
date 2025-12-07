from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.championship_competitor_dto import ChampionshipCompetitorDto
    from ..models.championship_event_dto import ChampionshipEventDto


T = TypeVar("T", bound="ChampionshipDataDto")


@_attrs_define
class ChampionshipDataDto:
    """
    Attributes:
        id (int | Unset):
        name (str | Unset):
        season (str | Unset):
        class_ (str | Unset):
        layout (int | Unset):
        events (list[ChampionshipEventDto] | Unset):
        competitors (list[ChampionshipCompetitorDto] | Unset):
    """

    id: int | Unset = UNSET
    name: str | Unset = UNSET
    season: str | Unset = UNSET
    class_: str | Unset = UNSET
    layout: int | Unset = UNSET
    events: list[ChampionshipEventDto] | Unset = UNSET
    competitors: list[ChampionshipCompetitorDto] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        season = self.season

        class_ = self.class_

        layout = self.layout

        events: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.events, Unset):
            events = []
            for events_item_data in self.events:
                events_item = events_item_data.to_dict()
                events.append(events_item)

        competitors: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.competitors, Unset):
            competitors = []
            for competitors_item_data in self.competitors:
                competitors_item = competitors_item_data.to_dict()
                competitors.append(competitors_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if season is not UNSET:
            field_dict["season"] = season
        if class_ is not UNSET:
            field_dict["class"] = class_
        if layout is not UNSET:
            field_dict["layout"] = layout
        if events is not UNSET:
            field_dict["events"] = events
        if competitors is not UNSET:
            field_dict["competitors"] = competitors

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.championship_competitor_dto import ChampionshipCompetitorDto
        from ..models.championship_event_dto import ChampionshipEventDto

        d = dict(src_dict)
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        season = d.pop("season", UNSET)

        class_ = d.pop("class", UNSET)

        layout = d.pop("layout", UNSET)

        _events = d.pop("events", UNSET)
        events: list[ChampionshipEventDto] | Unset = UNSET
        if _events is not UNSET:
            events = []
            for events_item_data in _events:
                events_item = ChampionshipEventDto.from_dict(events_item_data)

                events.append(events_item)

        _competitors = d.pop("competitors", UNSET)
        competitors: list[ChampionshipCompetitorDto] | Unset = UNSET
        if _competitors is not UNSET:
            competitors = []
            for competitors_item_data in _competitors:
                competitors_item = ChampionshipCompetitorDto.from_dict(competitors_item_data)

                competitors.append(competitors_item)

        championship_data_dto = cls(
            id=id,
            name=name,
            season=season,
            class_=class_,
            layout=layout,
            events=events,
            competitors=competitors,
        )

        championship_data_dto.additional_properties = d
        return championship_data_dto

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
