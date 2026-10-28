"""Finding and following the log file of a process."""

import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO

import psutil

STDOUT_STDERR = (1, 2)
BLOCK_SIZE = 8192


def find_log_file(pid: int) -> Path | None:
    """Return the file the process logs to: an open ``*.log`` file, or on macOS and Linux
    its stdout or stderr when redirected to a file."""
    try:
        files = psutil.Process(pid).open_files()
    except psutil.Error:
        return None
    for file in files:
        path = Path(file.path)
        if (file.fd in STDOUT_STDERR or path.suffix == ".log") and path.is_file():
            return path
    return None


def follow(path: Path, lines: int = 10, interval: float = 0.25) -> Iterator[str]:
    """Yield the last ``lines`` lines of ``path``, then each new line as it's written.

    Like ``tail -F``, this carries on when the log is truncated or rotated.
    """
    file = path.open("rb")
    try:
        for line in _last_lines(file, lines):
            yield line.decode(errors="replace")
        while True:
            line = file.readline()
            if line:
                yield line.decode(errors="replace")
            elif _replaced(path, file):
                file.close()
                file = path.open("rb")
            elif os.fstat(file.fileno()).st_size < file.tell():
                file.seek(0)  # truncated in place
            else:
                time.sleep(interval)
    finally:
        file.close()


def _last_lines(file: BinaryIO, count: int) -> list[bytes]:
    """Return the last ``count`` lines, reading backwards from the end of the file.

    Leaves the file positioned at its end.
    """
    end = file.seek(0, os.SEEK_END)
    start, chunk = end, b""
    while start > 0 and chunk.count(b"\n") <= count:
        start = max(0, start - BLOCK_SIZE)
        file.seek(start)
        chunk = file.read(end - start)
    return chunk.splitlines(keepends=True)[-count:] if count > 0 else []


def _replaced(path: Path, file: BinaryIO) -> bool:
    """Return True if ``path`` now names a different file, as after renaming log rotation."""
    try:
        return path.stat().st_ino != os.fstat(file.fileno()).st_ino
    except FileNotFoundError:
        return False  # mid-rotation, before the new file has been created
