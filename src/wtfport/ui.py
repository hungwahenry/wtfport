"""Everything wtfport shows in the terminal.

Values that come from the system (process names, commands, paths) are always wrapped in
``Text`` so that square brackets in them are never interpreted as Rich markup.
"""

import time
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from rich import box
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from wtfport.models import Listener, PortRecord, ProcessRecord

console = Console()
err_console = Console(stderr=True)


def info(message: str) -> None:
    console.print(Text(message))


def success(message: str) -> None:
    console.print(Text(message, style="green"))


def tip(message: str) -> None:
    console.print(Text(message, style="dim"))


def warning(message: str) -> None:
    err_console.print(Text(message, style="yellow"))


def error(message: str) -> None:
    err_console.print(Text(message, style="bold red"))


def event(message: str) -> None:
    """Print a line prefixed with the current time."""
    console.print(Text.assemble((datetime.now().strftime("%H:%M:%S"), "dim"), "  ", message))


def label(listener: Listener) -> str:
    """Describe a listener briefly, such as ``node (PID 1234)``."""
    if listener.pid is None:
        return "a process you can't see"
    return f"{listener.name or 'unknown'} (PID {listener.pid})"


def relative_time(timestamp: float) -> str:
    """Describe a past moment, such as ``3m ago``."""
    elapsed = time.time() - timestamp
    for suffix, seconds in (("d", 86_400), ("h", 3_600), ("m", 60)):
        if elapsed >= seconds:
            return f"{int(elapsed // seconds)}{suffix} ago"
    return "just now"


def listeners_table(listeners: Iterable[Listener]) -> Table:
    table = Table(title="Listening ports", box=box.ROUNDED)
    table.add_column("Port", style="cyan", justify="right")
    table.add_column("Process", style="green")
    table.add_column("PID", style="blue", justify="right")
    table.add_column("User", style="yellow")
    table.add_column("Started", style="magenta")
    for listener in listeners:
        table.add_row(
            str(listener.port),
            _value(listener.name),
            _value(listener.pid),
            _value(listener.user),
            _started(listener),
        )
    return table


def listener_panel(
    port: int, listeners: Iterable[Listener], url: str | None, log: Path | None
) -> Panel:
    rows: list[tuple[str, RenderableType]] = []
    for listener in listeners:
        if rows:
            rows.append(("", ""))
        rows += [
            ("Process", _value(listener.name)),
            ("PID", _value(listener.pid)),
            ("Command", _value(listener.command)),
            ("User", _value(listener.user)),
            ("Started", _started(listener)),
        ]
    if url is not None:
        rows.append(("URL", Text(url)))
    if log is not None:
        rows.append(("Log", Text(str(log))))
    return _panel(f"Port {port}", _grid(rows))


def menu(options: dict[str, str]) -> Table:
    """Show menu ``options``, a mapping of key to description."""
    return _grid(((key, Text(text)) for key, text in options.items()), key_style="bold cyan")


def key_values(rows: dict[str, str]) -> Table:
    return _grid((key, Text(value)) for key, value in rows.items())


def stats_summary(
    ports: list[PortRecord], processes: list[ProcessRecord], last_updated: str, limit: int = 5
) -> Group:
    top_ports = Table(title="Top ports", box=box.ROUNDED)
    top_ports.add_column("Port", style="cyan", justify="right")
    top_ports.add_column("Seen", style="green", justify="right")
    top_ports.add_column("Processes", style="yellow")
    top_ports.add_column("Last seen", style="magenta")
    for port in ports[:limit]:
        top_ports.add_row(
            str(port.port), str(port.count), _sample(port.processes), port.last_seen[:10]
        )

    top_processes = Table(title="Top processes", box=box.ROUNDED)
    top_processes.add_column("Process", style="green")
    top_processes.add_column("Seen", style="cyan", justify="right")
    top_processes.add_column("Ports", style="yellow")
    for process in processes[:limit]:
        top_processes.add_row(
            Text(process.name), str(process.count), _sample(map(str, process.ports))
        )

    summary = Text(
        f"Seen {len(ports)} ports and {len(processes)} processes, "
        f"most recently {_timestamp(last_updated)}."
    )
    return Group(summary, top_ports, *([top_processes] if processes else []))


def port_history(record: PortRecord) -> Panel:
    rows: list[tuple[str, RenderableType]] = [
        ("Seen", Text(f"{record.count} times")),
        ("First seen", Text(_timestamp(record.first_seen))),
        ("Last seen", Text(_timestamp(record.last_seen))),
        ("Processes", _value(", ".join(record.processes) or None)),
    ]
    return _panel(f"Port {record.port}", _grid(rows))


def _value(value: object) -> Text:
    return Text("unknown", style="dim") if value is None else Text(str(value))


def _started(listener: Listener) -> Text:
    if listener.started_at is None:
        return _value(None)
    return Text(relative_time(listener.started_at))


def _timestamp(iso: str) -> str:
    return iso.replace("T", " ")


def _sample(values: Iterable[str], limit: int = 3) -> Text:
    values = list(values)
    shown = ", ".join(values[:limit])
    if len(values) > limit:
        shown += f" +{len(values) - limit} more"
    return Text(shown)


def _grid(rows: Iterable[tuple[str, RenderableType]], key_style: str = "bold") -> Table:
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style=key_style, no_wrap=True)
    grid.add_column(overflow="fold")  # show long commands and paths in full
    for key, value in rows:
        grid.add_row(key, value)
    return grid


def _panel(title: str, body: RenderableType) -> Panel:
    return Panel(body, title=title, title_align="left", expand=False, padding=(1, 2))
