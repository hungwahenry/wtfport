"""Stopping processes."""

import contextlib
import time
from collections.abc import Iterable

import psutil

KILL_TIMEOUT = 1.0
POLL_INTERVAL = 0.05


def terminate(pids: Iterable[int], timeout: float = 3.0) -> list[int]:
    """Ask processes to exit, force-killing any still running after ``timeout`` seconds.

    Returns the pids that couldn't be stopped, usually for lack of permission. Windows
    can't ask a process to exit, so there both steps stop it immediately.
    """
    asked: list[psutil.Process] = []
    denied: list[int] = []
    for pid in pids:
        try:
            process = psutil.Process(pid)
            process.terminate()
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            denied.append(pid)
        else:
            asked.append(process)

    alive = _wait(asked, timeout)
    for process in alive:
        with contextlib.suppress(psutil.Error):
            process.kill()
    return denied + [process.pid for process in _wait(alive, KILL_TIMEOUT)]


def _wait(processes: list[psutil.Process], timeout: float) -> list[psutil.Process]:
    """Wait up to ``timeout`` seconds for processes to exit; return those still running."""
    deadline = time.monotonic() + timeout
    alive = [process for process in processes if _running(process)]
    while alive and time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL)
        alive = [process for process in alive if _running(process)]
    return alive


def _running(process: psutil.Process) -> bool:
    # A stopped process stays a zombie until its parent reaps it, but it no longer holds ports
    try:
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        return True
