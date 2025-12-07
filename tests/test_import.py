def test_import_event_results_client():
    import importlib

    pkg = importlib.import_module("event_results_client")
    assert hasattr(pkg, "Client")
