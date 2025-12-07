from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf8")


def test_get_event_sessions_has_main():
    p = Path("examples/get_event_sessions.py")
    src = _read(p)
    assert "def main(" in src or "async def main(" in src


def test_get_session_laps_has_main():
    p = Path("examples/get_session_laps.py")
    src = _read(p)
    assert "def main(" in src or "async def main(" in src


def test_exporter_has_main():
    p = Path("examples/export_announcements_by_org.py")
    src = _read(p)
    assert "def main(" in src or "async def main(" in src


def test_get_session_results_has_main():
    p = Path("examples/get_session_results.py")
    src = _read(p)
    assert "def main(" in src or "async def main(" in src
