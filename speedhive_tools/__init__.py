
"""
speedhive_tools
Public package entry point for the speedhive-tools library.

Exposes:
- SpeedHiveClient
- SpeedHiveAPIError
- __version__
"""


from __future__ import annotations

# Resolve package version from metadata if installed, else fall back.
try:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError  # Python 3.8+
except Exception:  # pragma: no cover
    _pkg_version = None

try:
    __version__ = _pkg_version("speedhive-tools") if _pkg_version else "0.0.0"
except PackageNotFoundError:  # not installed (editable or local usage)
    __version__ = "0.0.0"

# Re-export main client and error type. Provide a safe fallback for the error.
try:
    from .client import SpeedHiveClient, SpeedHiveAPIError
except ImportError:
    # If SpeedHiveAPIError isn't defined in client.py, define one here so imports work.
    from .client import SpeedHiveClient

    class SpeedHiveAPIError(Exception):
        """Raised when the Speedhive API returns an error or unexpected payload."""
        pass

