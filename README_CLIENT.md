# Event Results (Mylaps) client — quickstart

This repository contains a locally-generated OpenAPI client for the MyLaps Event Results API.

Quick steps:

1. Install the local package and its dependencies:

```bash
python -m pip install ./mylaps_client
python -m pip install -r requirements.txt
```

2. Run the example wrapper which queries server time:

```bash
python mylaps_client_wrapper.py
```

Notes:
- The generated package import name is `event_results_client` (see `./mylaps_client/event_results_client`).
- The wrapper uses the `system_time_controller` endpoint which does not require authentication.
