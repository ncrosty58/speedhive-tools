def test_package_and_submodules_importable():
    import importlib

    pkg = importlib.import_module("speedhive")
    assert pkg is not None

    # key submodules that should exist
    for mod in (
        "speedhive.cli.main",
        "speedhive.exporters.export_full_dump",
        "speedhive.analyzers.driver_laps",
        "speedhive.processing.lap_analysis",
    ):
        m = importlib.import_module(mod)
        assert m is not None
