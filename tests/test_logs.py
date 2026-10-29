import subprocess
import sys

import pytest

from wtfport import logs

OPENS_LOG = """
import sys, time
log = open(sys.argv[1], "a")
print("ready", flush=True)
time.sleep(60)
"""


def test_finds_open_log_file(tmp_path):
    log = tmp_path / "app.log"
    process = subprocess.Popen(
        [sys.executable, "-c", OPENS_LOG, str(log)], stdout=subprocess.PIPE, text=True
    )
    try:
        assert process.stdout is not None
        process.stdout.readline()
        assert logs.find_log_file(process.pid) == log
    finally:
        process.kill()
        process.wait()


@pytest.mark.skipif(sys.platform == "win32", reason="Windows doesn't report file descriptors")
def test_finds_redirected_stdout(tmp_path):
    output = tmp_path / "server.out"
    with output.open("w") as stdout:
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"], stdout=stdout
        )
    try:
        assert logs.find_log_file(process.pid) == output
    finally:
        process.kill()
        process.wait()


def test_no_log_file_for_missing_process():
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()

    assert logs.find_log_file(process.pid) is None


def test_follow_shows_tail_then_new_lines(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("".join(f"line {n}\n" for n in range(20)))
    lines = logs.follow(log, lines=3)

    assert [next(lines) for _ in range(3)] == ["line 17\n", "line 18\n", "line 19\n"]
    with log.open("a") as file:
        file.write("line 20\n")
    assert next(lines) == "line 20\n"


def test_follow_restarts_after_truncation(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("old line one\nold line two\n")
    lines = logs.follow(log, lines=2)
    next(lines), next(lines)

    log.write_text("new\n")
    assert next(lines) == "new\n"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows can't rename a file that is open")
def test_follow_continues_after_rotation(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("old\n")
    lines = logs.follow(log, lines=1)
    next(lines)

    log.rename(tmp_path / "app.log.1")
    log.write_text("new\n")
    assert next(lines) == "new\n"


def test_follow_reads_long_files_from_the_end(tmp_path):
    log = tmp_path / "app.log"
    log.write_bytes(b"".join(f"line {n}\n".encode() for n in range(100_000)) + "café\n".encode())

    lines = logs.follow(log, lines=2)

    assert [next(lines), next(lines)] == ["line 99999\n", "café\n"]


def test_follow_normalises_windows_line_endings(tmp_path):
    log = tmp_path / "app.log"
    log.write_bytes(b"one\r\ntwo\r\n")
    lines = logs.follow(log, lines=2)

    assert [next(lines), next(lines)] == ["one\n", "two\n"]
    with log.open("ab") as file:
        file.write(b"three\r\n")
    assert next(lines) == "three\n"
