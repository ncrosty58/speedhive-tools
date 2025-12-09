import importlib
import inspect


def _module_has_main(module_name: str) -> bool:
    try:
        mod = importlib.import_module(module_name)
    except Exception:
        return False

    if hasattr(mod, "main"):
        return inspect.isfunction(mod.main) or inspect.iscoroutinefunction(mod.main)
    return False


def test_export_sessions_has_main():
    assert _module_has_main("speedhive_tools.exporters.export_sessions")


def test_export_laps_has_main():
    assert _module_has_main("speedhive_tools.exporters.export_laps")


def test_export_announcements_has_main():
    assert _module_has_main("speedhive_tools.exporters.export_announcements")


def test_export_results_has_main():
    assert _module_has_main("speedhive_tools.exporters.export_results")


def test_export_events_has_main():
    assert _module_has_main("speedhive_tools.exporters.export_events")


def test_export_full_dump_has_main():
    assert _module_has_main("speedhive_tools.exporters.export_full_dump")
