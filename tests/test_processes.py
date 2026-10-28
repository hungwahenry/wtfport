import subprocess
import sys
import time

import pytest

from wtfport import processes

IGNORES_SIGTERM = """
import signal, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
print("ready", flush=True)
time.sleep(60)
"""


def test_terminates_process(server):
    process, _ = server

    assert processes.terminate([process.pid]) == []
    assert process.wait(timeout=5) is not None


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no SIGTERM to ignore")
def test_kills_process_that_ignores_terminate():
    process = subprocess.Popen(
        [sys.executable, "-c", IGNORES_SIGTERM], stdout=subprocess.PIPE, text=True
    )
    assert process.stdout is not None
    process.stdout.readline()

    assert processes.terminate([process.pid], timeout=0.5) == []
    assert process.wait(timeout=5) is not None


def test_already_exited_process_is_not_a_failure():
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()

    assert processes.terminate([process.pid]) == []


PARENT_THAT_NEVER_REAPS = """
import subprocess, sys, time
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
print(child.pid, flush=True)
time.sleep(60)
"""


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no zombie processes")
def test_unreaped_process_counts_as_stopped():
    # The killed child stays a zombie because its parent never waits for it
    parent = subprocess.Popen(
        [sys.executable, "-c", PARENT_THAT_NEVER_REAPS], stdout=subprocess.PIPE, text=True
    )
    try:
        assert parent.stdout is not None
        child = int(parent.stdout.readline())
        started = time.monotonic()

        assert processes.terminate([child]) == []
        assert time.monotonic() - started < 2
    finally:
        parent.kill()
        parent.wait()
