import importlib
import inspect


EXAMPLES = [
    "examples.example_server_time",
    "examples.example_get_events",
    "examples.example_get_event_sessions",
    "examples.example_get_session_laps",
    "examples.example_get_session_results",
    "examples.example_get_session_announcements",
    "examples.example_get_lap_chart",
    "examples.example_championships",
    "examples.example_track_records",
    "examples.example_get_organization",
]


def _module_has_main(module_name: str) -> bool:
    try:
        mod = importlib.import_module(module_name)
    except Exception:
        return False

    if hasattr(mod, "main"):
        return inspect.isfunction(mod.main) or inspect.iscoroutinefunction(mod.main)
    return False


def test_examples_have_main():
    missing = [m for m in EXAMPLES if not _module_has_main(m)]
    assert not missing, f"Modules missing main(): {missing}"
