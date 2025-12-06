
# speedhive-tools

A Python toolkit for interacting with the **MYLAPS Speedhive Event Results API** and automating the extraction of **track record announcements** (a.k.a. *announcements*) from event sessions.

> **Status:** Early, but usable. Public endpoints—no auth key required. Typed models (Pydantic v2), robust client, and ready-to-run examples are included.

---

## ✨ Features

- **Typed models** for Organizations, Events, Sessions, Announcements (Pydantic v2)
- **API Client** with retries, timeouts, logging, and offset/count pagination
- **End-to-end traversal**: Organization → Events → Sessions → Announcements
- **Utilities** for lap-time parsing, announcement text parsing, JSON/CSV I/O
- **Examples & runner scripts** for quick usage
- **Tests** (pytest) with stubbed HTTP

---

## 🔌 Supported Endpoints

The client targets the public Event Results API:

- List events across sport filters:
  ```http
  GET https://eventresults-api.speedhive.com/api/v0.2.3/eventresults/events?sport=All&sportCategory=Motorized&count=25&offset=0
  ```
- List events for an organization:
  ```http
  GET https://eventresults-api.speedhive.com/api/v0.2.3/eventresults/organizations/{ORGANIZATION_ID}/events?count=25&offset=0&sportCategory=Motorized
  ```
- Get an event with sessions:
  ```http
  GET https://eventresults-api.speedhive.com/api/v0.2.3/eventresults/events/{EVENT_ID}?sessions=true
  ```
- List announcements (track records) for a session:
  ```http
  GET https://eventresults-api.speedhive.com/api/v0.2.3/eventresults/sessions/{SESSION_ID}/announcements
  ```

> **Note:** These endpoints are derived from Speedhive’s public Event Results API. No API key is required for these read-only calls.

---

## 📦 Installation

### Option 1: Clone the repository
```bash
git clone https://github.com/ncrosty58/speedhive-tools.git
cd speedhive-tools
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -U pip
pip install -r requirements.txt  # or: pip install pydantic requests
```

### Option 2: Using `pyproject.toml`
If `pyproject.toml` lists dependencies:
```bash
pip install -e .
```

---

## 🧱 Project Structure

```
speedhive-tools/
├─ speedhive_tools/
│  ├─ __init__.py
│  ├─ client.py           # API client for Event Results
│  ├─ models.py           # Pydantic v2 models (Event, Session, Announcement, etc.)
│  ├─ utils.py            # Lap time parsing, I/O helpers, text parsing
├─ examples/
│  ├─ api_usage_demo.py   # Example usage of client + models
├─ example_runner.py      # Quick CLI for common workflows
├─ tests/
│  ├─ test_client.py      # Pytest with stubbed HTTP
├─ README.md
├─ LICENSE
├─ pyproject.toml
```

---

## 🚀 Quick Start

### Fetch announcements (track records) for an organization
```python
from speedhive_tools.client import SpeedHiveClient

client = SpeedHiveClient()
org_id = 30476  # Example: Waterford Hills
ann_map = client.fetch_org_announcements(
    org_id,
    count_events=25,
    offset_events=0,
    max_events=5,
    max_sessions_per_event=5,
)
print({sid: len(anns) for sid, anns in ann_map.items()})
```

### List events by organization
```python
from speedhive_tools.client import SpeedHiveClient

client = SpeedHiveClient()
org_events = client.list_events_by_organization(30476, count=25, offset=0)
for e in org_events[:5]:
    print(e.display_name, e.start_date, e.end_date)
```

### Get event + sessions, then list announcements for first session
```python
from speedhive_tools.client import SpeedHiveClient

client = SpeedHiveClient()
event = client.get_event_with_sessions(123456)
sessions = event.sessions or []
if sessions:
    session_id = sessions[0].resolved_id
    announcements = client.list_session_announcements(session_id)
    for a in announcements[:5]:
        print(a.driver_name, a.class_abbreviation, a.lap_time_seconds)
```

---

## 🛠️ Examples

Run the bundled examples to see the API in action:

```bash
# Organization details / events / records
python example_runner.py org 30476
python example_runner.py events 30476 --per-page 50 --top 5 --out out/events.json
python example_runner.py event-results 123456 --out out/event_123456.json
python example_runner.py records 30476 --json out/wh_records.json --csv out/wh_records.csv --show-seconds

# Direct API usage demo (typed models)
python examples/api_usage_demo.py
```

---

## 🧪 Testing

```bash
pip install pytest
pytest -q
```

- Tests use `pytest` + `monkeypatch` to stub network calls.
- Coverage can be added with `pytest-cov`.

---

## ⚙️ Configuration

No authentication is required for public endpoints. You can override defaults via environment variables:

- `SPEEDHIVE_BASE_URL` – default: `https://eventresults-api.speedhive.com/api/v0.2.3/eventresults`
- `SPEEDHIVE_USER_AGENT` – default: `speedhive-tools/1.0 (+https://github.com/ncrosty58/speedhive-tools)`

---

## 🧩 Notes & Caveats

- API response shapes can vary slightly (e.g., `items`, `events`, raw lists). Models use aliases and page wrappers to normalize these.
- Lap times may be strings (e.g., `"1:01.861"`) or numbers—in both cases we compute `lap_time_seconds` for convenience.
- If you share sample payloads, we can tighten model fields and add enums for session types.

---

## 📜 License

MIT — see `LICENSE`.

---

## 🙌 Contributing

PRs welcome! Please:
1. Open an issue describing your change.
2. Add/adjust tests.
3. Keep the README up-to-date.

---

## 💬 Contact

Maintainer: @ncrosty58

For questions or feature requests, open a GitHub issue in this repository.
