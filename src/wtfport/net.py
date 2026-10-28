"""Probes against ports on the local machine."""

import socket
import ssl
from http import HTTPStatus

LOOPBACK_HOSTS = ("127.0.0.1", "::1")


def is_port_open(port: int, timeout: float = 0.5) -> bool:
    """Return True if something accepts TCP connections on ``port`` over loopback."""
    sock = _connect(port, timeout)
    if sock is None:
        return False
    sock.close()
    return True


def web_url(port: int, timeout: float = 0.5) -> str | None:
    """Return the URL of the web server on ``port``, or None if it doesn't speak HTTP(S)."""
    status = _http_status(port, timeout)
    if status is not None and status != HTTPStatus.BAD_REQUEST:
        return f"http://localhost:{port}"
    # HTTPS servers such as nginx answer plain HTTP with 400. TLS is only tried now so
    # that plain HTTP servers don't log a garbled request every time a port is inspected.
    if _speaks_tls(port, timeout):
        return f"https://localhost:{port}"
    return None if status is None else f"http://localhost:{port}"


def _connect(port: int, timeout: float) -> socket.socket | None:
    for host in LOOPBACK_HOSTS:
        try:
            return socket.create_connection((host, port), timeout=timeout)
        except OSError:
            continue
    return None


def _http_status(port: int, timeout: float) -> int | None:
    """Send a HEAD request and return the response status, or None if it isn't HTTP."""
    sock = _connect(port, timeout)
    if sock is None:
        return None
    with sock:
        try:
            sock.sendall(b"HEAD / HTTP/1.0\r\nHost: localhost\r\n\r\n")
            status_line = sock.recv(32)
        except OSError:
            return None
    version, _, rest = status_line.partition(b" ")
    code = rest[:3]
    return int(code) if version.startswith(b"HTTP/") and code.isdigit() else None


def _speaks_tls(port: int, timeout: float) -> bool:
    sock = _connect(port, timeout)
    if sock is None:
        return False
    # Only the protocol matters here, not the server's identity
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with sock:
        try:
            with context.wrap_socket(sock, server_hostname="localhost"):
                return True
        except OSError:
            return False
