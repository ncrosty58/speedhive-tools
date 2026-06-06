import sys


def _run_with_argv(argv):
    import importlib

    cli = importlib.import_module("speedhive.cli.main")
    old = sys.argv
    try:
        sys.argv = argv
        try:
            code = cli.main()
            return code
        except SystemExit as e:
            return e.code
    finally:
        sys.argv = old
    return None


def test_cli_top_help():
    code = _run_with_argv(["speedhive", "--help"])
    assert code == 0


def test_cli_subcommand_helps():
    # Dynamically check help for each discovered module command
    import importlib
    discovery = importlib.import_module("speedhive.cli.discovery")
    cmds = [c for c, m, cat in discovery.discover_modules()]
    assert cmds, "No CLI modules discovered"
    for cmd in cmds:
        code = _run_with_argv(["speedhive", cmd, "--help"])
        assert code == 0, f"Help failed for subcommand: {cmd} (exit {code})"
