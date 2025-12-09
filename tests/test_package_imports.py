def test_package_and_submodules_importable():
    import importlib

    pkg = importlib.import_module("speedhive_tools")
    assert pkg is not None

    # key submodules that should exist after the refactor
    for mod in (
        "speedhive_tools.cli",
        "speedhive_tools.exporters.export_full_dump",
        "speedhive_tools.processors.process_full_dump",
        "speedhive_tools.analyzers.driver_laps",
        "speedhive_tools.utils.common",
    ):
        m = importlib.import_module(mod)
        assert m is not None
