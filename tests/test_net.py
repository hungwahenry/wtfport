import http.server
import shutil
import socket
import socketserver
import ssl
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from wtfport import net


@pytest.fixture(scope="session")
def certificate(tmp_path_factory) -> Path:
    """A throwaway self-signed certificate and key, generated so no key is committed."""
    if shutil.which("openssl") is None:
        pytest.skip("openssl not available")
    pem = tmp_path_factory.mktemp("tls") / "localhost.pem"
    subprocess.run(
        [
            *("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1"),
            *("-subj", "/CN=localhost", "-keyout", str(pem), "-out", str(pem)),
        ],
        check=True,
        capture_output=True,
    )
    return pem


@pytest.fixture
def https_port(certificate) -> Iterator[int]:
    """A port with a TLS-only server that completes handshakes and hangs up."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate)

    class Handshake(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            try:
                with context.wrap_socket(self.request, server_side=True):
                    pass
            except (OSError, ssl.SSLError):
                pass

    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handshake)
    threading.Thread(target=server.serve_forever, args=(0.05,), daemon=True).start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


@pytest.fixture
def bad_request_port() -> Iterator[int]:
    """A plain HTTP server that answers every request with 400 Bad Request."""

    class BadRequest(http.server.BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:
            self.send_error(400)

        def log_message(self, *args: object) -> None:
            pass

    server = socketserver.TCPServer(("127.0.0.1", 0), BadRequest)
    threading.Thread(target=server.serve_forever, args=(0.05,), daemon=True).start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


@pytest.fixture
def ipv6_port() -> Iterator[int]:
    try:
        sock = socket.socket(socket.AF_INET6)
        sock.bind(("::1", 0))
    except OSError:
        pytest.skip("IPv6 loopback unavailable")
    with sock:
        sock.listen()
        yield sock.getsockname()[1]


def test_open_port(listening_port):
    assert net.is_port_open(listening_port)


def test_closed_port(free_port):
    assert not net.is_port_open(free_port)


def test_ipv6_only_port(ipv6_port):
    assert net.is_port_open(ipv6_port)


def test_detects_http(http_port):
    assert net.web_url(http_port) == f"http://localhost:{http_port}"


def test_detects_https(https_port):
    assert net.web_url(https_port) == f"https://localhost:{https_port}"


def test_bad_request_without_tls_is_still_http(bad_request_port):
    assert net.web_url(bad_request_port) == f"http://localhost:{bad_request_port}"


def test_non_web_server(listening_port):
    assert net.web_url(listening_port, timeout=0.2) is None


def test_nothing_listening(free_port):
    assert net.web_url(free_port) is None
