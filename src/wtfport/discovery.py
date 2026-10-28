"""Find the processes listening on TCP ports."""

import shlex
import shutil
import subprocess
import sys

import psutil

from wtfport.models import Listener
from wtfport.net import is_port_open

LSOF_TIMEOUT = 10

# (port, pid) of a listening socket; pid is None when the owner isn't visible to us
Socket = tuple[int, int | None]


def list_listeners() -> list[Listener]:
    """Return every listening TCP socket, one entry per port and process."""
    return _describe(_listening_sockets())


def find_listeners(port: int) -> list[Listener]:
    """Return the processes listening on ``port``.

    When the port is in use but its owner can't be seen, the result is a single
    ``Listener`` with only ``port`` set.
    """
    return _describe(_listening_sockets(port))


def lsof_path() -> str | None:
    # macOS keeps lsof in /usr/sbin, which isn't on PATH for cron jobs and the like
    return shutil.which("lsof") or shutil.which("lsof", path="/usr/sbin:/usr/bin")


def _listening_sockets(port: int | None = None) -> set[Socket]:
    try:
        connections = psutil.net_connections(kind="tcp")
    except psutil.AccessDenied:
        # macOS only exposes the full socket table to root
        return _lsof_sockets(port)
    return {
        (conn.laddr.port, conn.pid)
        for conn in connections
        if conn.laddr  # empty for non-IP sockets
        and conn.status == psutil.CONN_LISTEN
        and (port is None or conn.laddr.port == port)
    }


def _lsof_sockets(port: int | None) -> set[Socket]:
    """Listening sockets according to lsof, which only sees the current user's processes."""
    sockets = _parse_lsof(_run_lsof(port))
    # Other users' sockets are invisible to lsof, but they still accept connections
    if port is not None and not sockets and is_port_open(port):
        sockets.add((port, None))
    return sockets


def _run_lsof(port: int | None) -> str:
    lsof = lsof_path()
    if lsof is None:
        return ""
    selector = "-iTCP" if port is None else f"-iTCP:{port}"
    try:
        result = subprocess.run(
            [lsof, "-nP", selector, "-sTCP:LISTEN", "-Fpn"],
            capture_output=True,
            text=True,
            check=False,  # lsof exits 1 when nothing matches
            timeout=LSOF_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout


def _parse_lsof(output: str) -> set[Socket]:
    # -F prints one field per line: "p<pid>" starts a process, "n<address>:<port>" is a socket
    sockets: set[Socket] = set()
    pid = None
    for line in output.splitlines():
        if line.startswith("p"):
            pid = int(line[1:])
        elif line.startswith("n"):
            port_text = line.rpartition(":")[2]
            if port_text.isdigit():
                sockets.add((int(port_text), pid))
    return sockets


def _describe(sockets: set[Socket]) -> list[Listener]:
    # A port can show up with and without a visible owner (e.g. its IPv4 and IPv6
    # sockets); the anonymous entry adds nothing then
    owned_ports = {port for port, pid in sockets if pid is not None}
    listeners = [
        listener
        for port, pid in sockets
        if pid is not None or port not in owned_ports
        if (listener := _listener(port, pid)) is not None
    ]
    return sorted(listeners, key=lambda listener: (listener.port, listener.pid or 0))


def _listener(port: int, pid: int | None) -> Listener | None:
    """Look up the process behind a socket; None if it has exited in the meantime."""
    if pid is None:
        return Listener(port)
    try:
        # Details we aren't allowed to read come back as None
        info = psutil.Process(pid).as_dict(
            attrs=["name", "cmdline", "username", "create_time"], ad_value=None
        )
    except psutil.NoSuchProcess:
        return None
    return Listener(
        port=port,
        pid=pid,
        name=info["name"],
        command=_join_command(info["cmdline"]),
        user=info["username"],
        started_at=info["create_time"],
    )


def _join_command(argv: list[str] | None) -> str | None:
    """Quote ``argv`` so the command can be pasted back into a shell."""
    if not argv:
        return None
    return subprocess.list2cmdline(argv) if sys.platform == "win32" else shlex.join(argv)
