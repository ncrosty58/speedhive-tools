"""Backward-compatible CLI shim for legacy `speedhive_tools` import path."""
from __future__ import annotations

from speedhive.cli.main import main
from speedhive.cli.discovery import discover_modules as _discover_modules

__all__ = ["main", "_discover_modules"]


if __name__ == "__main__":
    raise SystemExit(main())
