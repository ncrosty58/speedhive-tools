from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.lap_difference import LapDifference


T = TypeVar("T", bound="LapComparison")


@_attrs_define
class LapComparison:
    """
    Attributes:
        position (int | Unset):
        leader_lap (int | Unset):
        diff (LapDifference | Unset):
        gap_ahead (LapDifference | Unset):
        gap_behind (LapDifference | Unset):
    """

    position: int | Unset = UNSET
    leader_lap: int | Unset = UNSET
    diff: LapDifference | Unset = UNSET
    gap_ahead: LapDifference | Unset = UNSET
    gap_behind: LapDifference | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        position = self.position

        leader_lap = self.leader_lap

        diff: dict[str, Any] | Unset = UNSET
        if not isinstance(self.diff, Unset):
            diff = self.diff.to_dict()

        gap_ahead: dict[str, Any] | Unset = UNSET
        if not isinstance(self.gap_ahead, Unset):
            gap_ahead = self.gap_ahead.to_dict()

        gap_behind: dict[str, Any] | Unset = UNSET
        if not isinstance(self.gap_behind, Unset):
            gap_behind = self.gap_behind.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if position is not UNSET:
            field_dict["position"] = position
        if leader_lap is not UNSET:
            field_dict["leaderLap"] = leader_lap
        if diff is not UNSET:
            field_dict["diff"] = diff
        if gap_ahead is not UNSET:
            field_dict["gapAhead"] = gap_ahead
        if gap_behind is not UNSET:
            field_dict["gapBehind"] = gap_behind

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lap_difference import LapDifference

        d = dict(src_dict)
        position = d.pop("position", UNSET)

        leader_lap = d.pop("leaderLap", UNSET)

        _diff = d.pop("diff", UNSET)
        diff: LapDifference | Unset
        if isinstance(_diff, Unset):
            diff = UNSET
        else:
            diff = LapDifference.from_dict(_diff)

        _gap_ahead = d.pop("gapAhead", UNSET)
        gap_ahead: LapDifference | Unset
        if isinstance(_gap_ahead, Unset):
            gap_ahead = UNSET
        else:
            gap_ahead = LapDifference.from_dict(_gap_ahead)

        _gap_behind = d.pop("gapBehind", UNSET)
        gap_behind: LapDifference | Unset
        if isinstance(_gap_behind, Unset):
            gap_behind = UNSET
        else:
            gap_behind = LapDifference.from_dict(_gap_behind)

        lap_comparison = cls(
            position=position,
            leader_lap=leader_lap,
            diff=diff,
            gap_ahead=gap_ahead,
            gap_behind=gap_behind,
        )

        lap_comparison.additional_properties = d
        return lap_comparison

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
