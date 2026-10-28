"""The port history: which ports wtfport has seen in use, and the processes that held them."""

import contextlib
import json
import os
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from wtfport.models import Listener, PortRecord, ProcessRecord

SCHEMA_VERSION = 1

T = TypeVar("T")


def default_path() -> Path:
    return Path.home() / ".wtfport" / "stats.json"


class StatsStore:
    """Sighting counts kept in a local JSON file.

    A missing or malformed file starts a fresh history, and failing to save is ignored:
    the history is a convenience and must never break a command.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_path()
        self.last_updated: str | None = None
        self._ports: dict[int, PortRecord] = {}
        self._processes: dict[str, ProcessRecord] = {}
        self._load()

    def record(self, listeners: Iterable[Listener]) -> None:
        """Count one sighting of each port, and of each process on it, then save."""
        names_by_port: dict[int, set[str]] = {}
        for listener in listeners:
            names = names_by_port.setdefault(listener.port, set())
            if listener.name is not None:
                names.add(listener.name)
        if not names_by_port:
            return

        now = datetime.now().isoformat(timespec="seconds")
        for port, names in names_by_port.items():
            seen = self._ports.get(port, PortRecord(port, 0, now, now, ()))
            self._ports[port] = replace(
                seen,
                count=seen.count + 1,
                last_seen=now,
                processes=_merge(seen.processes, sorted(names)),
            )
            for name in names:
                process = self._processes.get(name, ProcessRecord(name, 0, now, now, ()))
                self._processes[name] = replace(
                    process,
                    count=process.count + 1,
                    last_seen=now,
                    ports=_merge(process.ports, [port]),
                )
        self.last_updated = now
        self._save()

    def ports(self) -> list[PortRecord]:
        """Every port seen, most often seen first."""
        return sorted(self._ports.values(), key=lambda record: (-record.count, record.port))

    def processes(self) -> list[ProcessRecord]:
        """Every process seen, most often seen first."""
        return sorted(self._processes.values(), key=lambda record: (-record.count, record.name))

    def port(self, port: int) -> PortRecord | None:
        return self._ports.get(port)

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data["version"] != SCHEMA_VERSION:
                return
            ports = {
                int(port): PortRecord(
                    port=int(port),
                    count=int(entry["count"]),
                    first_seen=str(entry["first_seen"]),
                    last_seen=str(entry["last_seen"]),
                    processes=tuple(map(str, entry["processes"])),
                )
                for port, entry in data["ports"].items()
            }
            processes = {
                str(name): ProcessRecord(
                    name=str(name),
                    count=int(entry["count"]),
                    first_seen=str(entry["first_seen"]),
                    last_seen=str(entry["last_seen"]),
                    ports=tuple(map(int, entry["ports"])),
                )
                for name, entry in data["processes"].items()
            }
            last_updated = data["last_updated"]
        except (OSError, ValueError, LookupError, TypeError, AttributeError):
            return  # missing or malformed: start a fresh history
        self._ports, self._processes = ports, processes
        self.last_updated = None if last_updated is None else str(last_updated)

    def _save(self) -> None:
        data = {
            "version": SCHEMA_VERSION,
            "last_updated": self.last_updated,
            "ports": {str(record.port): _entry(record, "port") for record in self._ports.values()},
            "processes": {
                record.name: _entry(record, "name") for record in self._processes.values()
            },
        }
        # Write a temporary file and rename it into place so the history is never half-written
        with contextlib.suppress(OSError):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".stats-", suffix=".tmp")
            temporary = Path(name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as file:
                    json.dump(data, file, indent=2)
                _give_to_home_owner(self.path.parent, temporary)
                temporary.replace(self.path)
            finally:
                temporary.unlink(missing_ok=True)


def _merge(existing: tuple[T, ...], new: Iterable[T]) -> tuple[T, ...]:
    """Append the items of ``new`` that aren't in ``existing`` yet, keeping the order."""
    return tuple(dict.fromkeys([*existing, *new]))


def _entry(record: PortRecord | ProcessRecord, key: str) -> dict[str, Any]:
    """A record as stored in the file, where it is keyed by its ``key`` field."""
    return {field: value for field, value in asdict(record).items() if field != key}


def _give_to_home_owner(directory: Path, *paths: Path) -> None:
    """Under sudo, hand the history back to the user whose home it lives in.

    macOS keeps ``HOME`` under sudo, so root would otherwise create files in the user's
    home that the user can't read or replace afterwards.
    """
    if sys.platform == "win32" or os.geteuid() != 0:
        return
    owner = directory.parent.stat()
    for path in (directory, *paths):
        os.chown(path, owner.st_uid, owner.st_gid)
