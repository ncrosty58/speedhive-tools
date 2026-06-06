def test_import_generated_client():
    import importlib

    pkg = importlib.import_module("speedhive.generated.client")
    assert hasattr(pkg, "Client")
