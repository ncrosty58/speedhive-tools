"""Stub LiveTimingClient for future realtime/live-timing support.

This module provides a placeholder API for a dedicated live-timing client that
would connect to a realtime backend (WebSocket/SSE) used by Speedhive's
live-timing frontend. At the moment there is no public documented realtime
API exposed by MyLaps that we can safely implement against without reverse
engineering the web app. This file intentionally contains only stubs and
clear TODO markers for future implementation when an API for live streaming
becomes available.

Usage (stubbed):
    from mylaps_live_client import LiveTimingClient

    client = LiveTimingClient(token=MYTOKEN)
    # TODO: implement connect(), subscribe to sessions, wire callbacks

Why a separate client?
 - Live timing typically uses a different protocol (WebSocket/SSE) and
   different authentication/authorization mechanisms than the REST API.
 - Separating the live client keeps polling logic and realtime message
   handling separate from the REST wrapper (`mylaps_client_wrapper.py`).

TODOs:
 - Investigate official MyLaps/Speedhive realtime developer docs / SDKs.
 - If an official WebSocket/SSE endpoint is provided, implement an async
   client using `websockets` or `aiohttp` for WebSocket and `sseclient`
   or `aiohttp` for SSE.
 - Add token/session/key negotiation if required by the realtime service.
 - Add retries, reconnect/backoff, heartbeats, and rate-limiting.
 - Provide a synchronous wrapper that falls back to efficient polling using
   the REST API if realtime is not available.
"""
from __future__ import annotations

from typing import Any, Callable, Optional


class LiveTimingClient:
    """Placeholder client for Speedhive/MyLaps live timing.

    This class intentionally contains stubs. Implementers should replace
    the methods with real WebSocket/SSE connection logic when an official
    realtime API or protocol is available.
    """

    def __init__(self, token: Optional[str] = None, base_url: str | None = None, *, timeout: float = 30.0):
        """Create a LiveTimingClient.

        Args:
            token: Optional API token if required by the realtime API.
            base_url: Optional realtime base URL (e.g., wss://realtime.mylaps.com).
            timeout: Network timeout for fallback operations.
        """
        self.token = token
        self.base_url = base_url or "wss://speedhive.mylaps.com/livetiming"
        self.timeout = timeout

        # internal state placeholders
        self._connected = False

    def connect(self) -> None:
        """Open a connection to the realtime service.

        TODO: implement WebSocket/SSE connect logic. Consider async API.
        """
        raise NotImplementedError("LiveTimingClient.connect() is not implemented yet. See TODO in mylaps_live_client.py")

    def close(self) -> None:
        """Close the realtime connection and clean up resources."""
        raise NotImplementedError("LiveTimingClient.close() is not implemented yet.")

    def subscribe_session(self, session_key: str | int, callback: Callable[[dict], Any]) -> None:
        """Subscribe to realtime updates for a session.

        Args:
            session_key: A session identifier or session key used by the realtime API.
            callback: Callable invoked with parsed event dicts when messages arrive.

        Note: For the Speedhive web UI the session identifier in the URL looks
        like a GUID+int combination (e.g., FDA3FA40...-2147484492-1073743335).
        The mapping from that string to any REST session id (numeric) is not
        documented and must not be reverse-engineered here.
        """
        raise NotImplementedError("LiveTimingClient.subscribe_session() is a TODO.")

    def subscribe_announcements(self, session_key: str | int, callback: Callable[[dict], Any]) -> None:
        """Subscribe to announcement messages for a session (e.g., text updates)."""
        raise NotImplementedError("LiveTimingClient.subscribe_announcements() is a TODO.")

    def start_polling_fallback(self, session_id: int, callback: Callable[[dict], Any], interval: float = 1.0) -> None:
        """Fallback: start a polling loop that calls the REST API and invokes callback for new rows.

        This should be implemented as a cooperative coroutine or background
        thread in the future. For now this is a placeholder to document the
        intended behavior.
        """
        raise NotImplementedError("LiveTimingClient.start_polling_fallback() is a TODO.")


__all__ = ["LiveTimingClient"]
