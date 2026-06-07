import argparse
from unittest.mock import patch

from speedhive.cli.main import default_db_path, main


@patch("speedhive.cli.main._run_module_as_main")
def test_export_dump_dispatches(mock_run):
    with patch("sys.argv", ["speedhive", "export-dump", "--org", "30476"]):
        try:
            main()
        except SystemExit:
            pass
    mock_run.assert_called_once_with(
        "speedhive.exporters.export_full_dump",
        ["--org", "30476", "--output", "./output"],
    )

@patch("speedhive.cli.main._run_module_as_main")
def test_report_consistency(mock_run):
    with patch(
        "sys.argv",
        ["speedhive", "report-consistency", "--org", "30476", "--top", "5"],
    ):
        try:
            main()
        except SystemExit:
            pass
    args_list = mock_run.call_args[0][1]
    assert "--org" in args_list
    assert "30476" in args_list
    assert "--top" in args_list
    assert "5" in args_list


@patch("speedhive.cli.main._run_module_as_main")
def test_sync_org_dispatches_without_legacy_cache_root(mock_run):
    with patch(
        "sys.argv",
        [
            "speedhive",
            "sync-org",
            "--org",
            "30476",
            "--mode",
            "incremental",
            "--recent-backfill-events",
            "3",
        ],
    ):
        try:
            main()
        except SystemExit:
            pass
    mock_run.assert_called_once_with(
        "speedhive.exporters.export_org_cache",
        [
            "--org",
            "30476",
            "--db-path",
            str(default_db_path()),
            "--mode",
            "incremental",
            "--recent-backfill-events",
            "3",
        ],
    )


@patch("speedhive.cli.main._run_module_as_main")
def test_import_dump_dispatches(mock_run):
    with patch("sys.argv", ["speedhive", "import-dump", "--org", "30476"]):
        try:
            main()
        except SystemExit:
            pass
    mock_run.assert_called_once_with(
        "speedhive.processing.process_sqlite_import",
        ["--org", "30476"],
    )


def test_discovery_registers_builtin():
    import argparse
    from speedhive.cli.discovery import register_discovered

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    register_discovered(sub)
    choices = list(sub.choices.keys())
    assert "export-dump" in choices
    assert "sync-org" in choices
    assert "report-consistency" in choices


@patch("speedhive.cli.main._run_module_as_main")
def test_export_lap_records_dispatches(mock_run):
    with patch(
        "sys.argv",
        [
            "speedhive",
            "export-lap-records",
            "--org",
            "30476",
            "--max-events",
            "10",
        ],
    ):
        try:
            main()
        except SystemExit:
            pass
    mock_run.assert_called_once_with(
        "speedhive.exporters.export_lap_records",
        ["--org", "30476", "--max-events", "10"],
    )
