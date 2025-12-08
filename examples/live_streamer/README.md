Live Streamer examples
======================

This folder contains a simple, polling-based example for streaming lap
updates using the official MyLaps REST API. It intentionally avoids any
reverse-engineered discovery or scraping behavior and provides a clear
integration point for a future realtime client.

Files
-----
- `stream_laps.py`: A minimal polling example that requires a known
  `--session` id and periodically fetches lap rows using
  `SpeedhiveClient.get_laps()`. Use this as a fallback while a documented
  realtime API is not available.

- `find_live_orgs.py`: A REST-only helper that lists recent events for a
  specific organization (`--org`). It does not attempt broad scanning or
  unauthenticated discovery; such endpoints may require authentication or
  a separate realtime API.

Realtime / future work
----------------------

The repository includes a stubbed realtime client: `mylaps_live_client.py`.
When an official realtime API (WebSocket/SSE or similar) and its message
formats are available, implement `LiveTimingClient` and replace or augment
the polling fallback in `stream_laps.py`.

How to run
----------
Example: poll a session for new lap rows and print JSON lines

```bash
PYTHONPATH=. python examples/live_streamer/stream_laps.py --session 12345 --token "$MYTOKEN" --json
```

Notes
-----
- Avoid broad, unauthenticated scanning of the public web UI. Use the
  official API and authenticated endpoints where required.
- If you need help implementing the realtime client, open an issue or
  provide the realtime API spec and I can add an implementation.
