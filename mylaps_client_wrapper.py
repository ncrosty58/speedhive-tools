"""Backward-compatible wrapper around `speedhive.wrapper.SpeedhiveClient`."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from speedhive.wrapper import SpeedhiveClient as _SpeedhiveClient


@dataclass
class SpeedhiveClient:
    """Legacy constructor-based wrapper kept for compatibility."""

    base_url: str = "https://api2.mylaps.com"
    token: Optional[str] = None
    timeout: float = 30.0
    _delegate: _SpeedhiveClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._delegate = _SpeedhiveClient.create(
            base_url=self.base_url,
            token=self.token,
            timeout=self.timeout,
        )

    @classmethod
    def create(
        cls,
        base_url: str = "https://api2.mylaps.com",
        token: Optional[str] = None,
        timeout: float = 30.0,
        **_: Any,
    ) -> "SpeedhiveClient":
        return cls(base_url=base_url, token=token, timeout=timeout)

    @staticmethod
    def _parse_response(response) -> Any:
        if not response.content:
            return None
        return json.loads(response.content)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._delegate, item)
