def test_package_and_submodules_importable():
    import importlib

    pkg = importlib.import_module("speedhive")
    assert pkg is not None

    # key submodules that should exist
    for mod in (
        "speedhive.cli.main",
        "speedhive.exporters.export_full_dump",
        "speedhive.exporters.export_curated_track_records",
        "speedhive.analyzers.analyze_driver_laps",
        "speedhive.analysis.lap_analysis",
        "speedhive.workflows.refresh_org_cache",
        "speedhive.workflows.import_sqlite_dump",
        "speedhive.workflows.track_records.extract",
        "speedhive.workflows.track_records.curation",
        "speedhive.workflows.track_records.import_curated",
        "speedhive.stores.track_records",
    ):
        m = importlib.import_module(mod)
        assert m is not None
