"""Helpers for exporting track-record workflow history snapshots."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from speedhive.ndjson import save_ndjson


def save_candidates_history_ndjson(path: Path, payload: Dict[str, Any]) -> None:
    save_ndjson(path, payload, "candidates")
