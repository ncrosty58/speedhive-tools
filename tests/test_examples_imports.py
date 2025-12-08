from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf8")


def test_export_sessions_has_main():
    p = Path("examples/export_sessions.py")
    src = _read(p)
    assert "def main(" in src or "async def main(" in src


def test_export_laps_has_main():
    p = Path("examples/export_laps.py")
    src = _read(p)
    assert "def main(" in src or "async def main(" in src


def test_export_announcements_has_main():
    p = Path("examples/export_announcements.py")
    src = _read(p)
    assert "def main(" in src or "async def main(" in src


def test_export_results_has_main():
    p = Path("examples/export_results.py")
    src = _read(p)
    assert "def main(" in src or "async def main(" in src


def test_export_events_has_main():
    p = Path("examples/export_events.py")
    src = _read(p)
    assert "def main(" in src or "async def main(" in src


def test_export_full_dump_has_main():
    p = Path("examples/export_full_dump.py")
    src = _read(p)
    assert "def main(" in src or "async def main(" in src
