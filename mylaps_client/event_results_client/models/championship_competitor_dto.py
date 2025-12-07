from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.championship_competitor_event_dto import ChampionshipCompetitorEventDto


T = TypeVar("T", bound="ChampionshipCompetitorDto")


@_attrs_define
class ChampionshipCompetitorDto:
    """
    Attributes:
        no (str | Unset):
        first_name (str | Unset):
        last_name (str | Unset):
        class_ (str | Unset):
        position (str | Unset):
        total (float | Unset):
        dropped (int | Unset):
        diff (float | Unset):
        gap (float | Unset):
        events (list[ChampionshipCompetitorEventDto] | Unset):
    """

    no: str | Unset = UNSET
    first_name: str | Unset = UNSET
    last_name: str | Unset = UNSET
    class_: str | Unset = UNSET
    position: str | Unset = UNSET
    total: float | Unset = UNSET
    dropped: int | Unset = UNSET
    diff: float | Unset = UNSET
    gap: float | Unset = UNSET
    events: list[ChampionshipCompetitorEventDto] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        no = self.no

        first_name = self.first_name

        last_name = self.last_name

        class_ = self.class_

        position = self.position

        total = self.total

        dropped = self.dropped

        diff = self.diff

        gap = self.gap

        events: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.events, Unset):
            events = []
            for events_item_data in self.events:
                events_item = events_item_data.to_dict()
                events.append(events_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if no is not UNSET:
            field_dict["no"] = no
        if first_name is not UNSET:
            field_dict["firstName"] = first_name
        if last_name is not UNSET:
            field_dict["lastName"] = last_name
        if class_ is not UNSET:
            field_dict["class"] = class_
        if position is not UNSET:
            field_dict["position"] = position
        if total is not UNSET:
            field_dict["total"] = total
        if dropped is not UNSET:
            field_dict["dropped"] = dropped
        if diff is not UNSET:
            field_dict["diff"] = diff
        if gap is not UNSET:
            field_dict["gap"] = gap
        if events is not UNSET:
            field_dict["events"] = events

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.championship_competitor_event_dto import ChampionshipCompetitorEventDto

        d = dict(src_dict)
        no = d.pop("no", UNSET)

        first_name = d.pop("firstName", UNSET)

        last_name = d.pop("lastName", UNSET)

        class_ = d.pop("class", UNSET)

        position = d.pop("position", UNSET)

        total = d.pop("total", UNSET)

        dropped = d.pop("dropped", UNSET)

        diff = d.pop("diff", UNSET)

        gap = d.pop("gap", UNSET)

        _events = d.pop("events", UNSET)
        events: list[ChampionshipCompetitorEventDto] | Unset = UNSET
        if _events is not UNSET:
            events = []
            for events_item_data in _events:
                events_item = ChampionshipCompetitorEventDto.from_dict(events_item_data)

                events.append(events_item)

        championship_competitor_dto = cls(
            no=no,
            first_name=first_name,
            last_name=last_name,
            class_=class_,
            position=position,
            total=total,
            dropped=dropped,
            diff=diff,
            gap=gap,
            events=events,
        )

        championship_competitor_dto.additional_properties = d
        return championship_competitor_dto

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
