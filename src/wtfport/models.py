"""Data types shared across wtfport."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Listener:
    """A process listening on a TCP port.

    Every field except ``port`` is ``None`` when the operating system won't show it to
    the current user, typically because the process belongs to someone else.
    """

    port: int
    pid: int | None = None
    name: str | None = None
    command: str | None = None
    user: str | None = None
    started_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready dict, with ``started_at`` as an ISO 8601 local time."""
        started_at = (
            None
            if self.started_at is None
            else datetime.fromtimestamp(self.started_at).astimezone().isoformat(timespec="seconds")
        )
        return {**asdict(self), "started_at": started_at}


@dataclass(frozen=True)
class PortRecord:
    """How often a port has been seen in use, and by which processes."""

    port: int
    count: int
    first_seen: str
    last_seen: str
    processes: tuple[str, ...]


@dataclass(frozen=True)
class ProcessRecord:
    """How often a process has been seen listening, and on which ports."""

    name: str
    count: int
    first_seen: str
    last_seen: str
    ports: tuple[int, ...]
