import argparse
from unittest.mock import patch

from speedhive.cli.main import main


@patch("speedhive.cli.main._run_module_as_main")
def test_export_full_dump_dispatches(mock_run):
    with patch("sys.argv", ["speedhive", "export-full-dump", "--org", "30476"]):
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
