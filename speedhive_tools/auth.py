
"""
auth.py
Authentication and configuration helpers for Speedhive tools.

Since Speedhive API does not require authentication for public endpoints,
this module focuses on:
- Environment variable configuration
- Optional header injection for future use
"""

import os
from typing import Dict


def get_default_headers() -> Dict[str, str]:
    """
    Return default headers for Speedhive API requests.
    Adjust if Speedhive requires specific headers in the future.
    """
    return {
        "Accept": "application/json",
        "User-Agent": os.getenv("SPEEDHIVE_USER_AGENT", "speedhive-tools/1.0")
    }


def get_base_url() -> str:
    """
    Get the base URL for Speedhive API from environment or default.
    """
    return os.getenv("SPEEDHIVE_BASE_URL", "https://eventresults-api.speedhive.com/api/v0.2.3/eventresults")


def attach_headers(session) -> None:
    """
    Attach default headers to a requests.Session.
    """
    session.headers.update(get_default_headers())
