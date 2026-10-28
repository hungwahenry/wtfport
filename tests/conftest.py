import http.server
import socket
import socketserver
import subprocess
import sys
import threading
from collections.abc import Iterator

import pytest

SERVER = """
import socket, time
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
sock.listen()
print(sock.getsockname()[1], flush=True)
time.sleep(60)
"""


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Keep the stats file out of the real home directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


@pytest.fixture
def listening_port() -> Iterator[int]:
    """A port this test process is listening on."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        yield sock.getsockname()[1]


@pytest.fixture
def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def http_port() -> Iterator[int]:
    """A port with an HTTP server running in a background thread."""

    class QuietHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

    # A plain TCPServer: http.server.HTTPServer does a reverse DNS lookup that can stall
    server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, args=(0.05,), daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


@pytest.fixture
def server() -> Iterator[tuple[subprocess.Popen[str], int]]:
    """A separate process listening on a port; yields the process and the port."""
    process = subprocess.Popen([sys.executable, "-c", SERVER], stdout=subprocess.PIPE, text=True)
    assert process.stdout is not None
    port = int(process.stdout.readline())
    yield process, port
    process.kill()
    process.wait()
