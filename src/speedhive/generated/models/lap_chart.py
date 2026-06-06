from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.lap_position import LapPosition
    from ..models.results_competitor import ResultsCompetitor


T = TypeVar("T", bound="LapChart")


@_attrs_define
class LapChart:
    """
    Attributes:
        id (int | Unset):
        event_id (int | Unset):
        number_of_laps (int | Unset):
        event_ref (str | Unset):
        position_rows (list[list[LapPosition]] | Unset):
        start_positions (list[ResultsCompetitor] | Unset):
    """

    id: int | Unset = UNSET
    event_id: int | Unset = UNSET
    number_of_laps: int | Unset = UNSET
    event_ref: str | Unset = UNSET
    position_rows: list[list[LapPosition]] | Unset = UNSET
    start_positions: list[ResultsCompetitor] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        event_id = self.event_id

        number_of_laps = self.number_of_laps

        event_ref = self.event_ref

        position_rows: list[list[dict[str, Any]]] | Unset = UNSET
        if not isinstance(self.position_rows, Unset):
            position_rows = []
            for position_rows_item_data in self.position_rows:
                position_rows_item = []
                for position_rows_item_item_data in position_rows_item_data:
                    position_rows_item_item = position_rows_item_item_data.to_dict()
                    position_rows_item.append(position_rows_item_item)

                position_rows.append(position_rows_item)

        start_positions: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.start_positions, Unset):
            start_positions = []
            for start_positions_item_data in self.start_positions:
                start_positions_item = start_positions_item_data.to_dict()
                start_positions.append(start_positions_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if event_id is not UNSET:
            field_dict["eventId"] = event_id
        if number_of_laps is not UNSET:
            field_dict["numberOfLaps"] = number_of_laps
        if event_ref is not UNSET:
            field_dict["eventRef"] = event_ref
        if position_rows is not UNSET:
            field_dict["positionRows"] = position_rows
        if start_positions is not UNSET:
            field_dict["startPositions"] = start_positions

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lap_position import LapPosition
        from ..models.results_competitor import ResultsCompetitor

        d = dict(src_dict)
        id = d.pop("id", UNSET)

        event_id = d.pop("eventId", UNSET)

        number_of_laps = d.pop("numberOfLaps", UNSET)

        event_ref = d.pop("eventRef", UNSET)

        _position_rows = d.pop("positionRows", UNSET)
        position_rows: list[list[LapPosition]] | Unset = UNSET
        if _position_rows is not UNSET:
            position_rows = []
            for position_rows_item_data in _position_rows:
                position_rows_item = []
                _position_rows_item = position_rows_item_data
                for position_rows_item_item_data in _position_rows_item:
                    position_rows_item_item = LapPosition.from_dict(position_rows_item_item_data)

                    position_rows_item.append(position_rows_item_item)

                position_rows.append(position_rows_item)

        _start_positions = d.pop("startPositions", UNSET)
        start_positions: list[ResultsCompetitor] | Unset = UNSET
        if _start_positions is not UNSET:
            start_positions = []
            for start_positions_item_data in _start_positions:
                start_positions_item = ResultsCompetitor.from_dict(start_positions_item_data)

                start_positions.append(start_positions_item)

        lap_chart = cls(
            id=id,
            event_id=event_id,
            number_of_laps=number_of_laps,
            event_ref=event_ref,
            position_rows=position_rows,
            start_positions=start_positions,
        )

        lap_chart.additional_properties = d
        return lap_chart

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
