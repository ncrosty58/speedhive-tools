import os
import sys
import subprocess
import shlex
import textwrap


def test_stream_laps_demo_runs_and_prints_demo_message(tmp_path):
    """Run the demo mode of `stream_laps.py` for a short duration and
    assert it prints demo messages / callback output without network.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script = os.path.join(repo_root, "examples", "live_streamer", "stream_laps.py")

    # Use a short demo duration so the process exits quickly
    cmd = f"{sys.executable} {shlex.quote(script)} --session 1 --json --demo-duration 1.5"

    # Run with PYTHONPATH set to repo root so examples can import local modules
    env = os.environ.copy()
    env["PYTHONPATH"] = repo_root

    proc = subprocess.run(cmd, shell=True, capture_output=True, env=env, timeout=10)
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")

    # Expect the demo message or demo callback to appear in stdout
    assert "Demo mode" in out or "Polling fallback started" in out or "[demo callback]" in out
    # No uncaught exceptions printed to stderr
    assert "Traceback" not in err
