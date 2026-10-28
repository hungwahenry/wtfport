"""What each command does. Every action returns the process exit code."""

import contextlib
import getpass
import json
import platform
import sys
import time
import webbrowser
from collections.abc import Callable, Iterable, Iterator
from dataclasses import asdict
from functools import partial
from pathlib import Path
from typing import Any

from rich.prompt import Confirm, Prompt
from rich.text import Text

from wtfport import __version__, discovery, logs, net, processes, system, ui
from wtfport.models import Listener
from wtfport.stats import StatsStore, default_path

OK = 0
FAILURE = 1
POLL_INTERVAL = 1.0


def show_all(as_json: bool) -> int:
    listeners = _remember(discovery.list_listeners())
    if as_json:
        _print_json([listener.to_dict() for listener in listeners])
        return OK
    if listeners:
        ui.console.print(ui.listeners_table(listeners))
        ui.tip("Run `wtfport <port>` for details and actions.")
    else:
        ui.info("No listening TCP ports found.")
    _privilege_tip()
    return OK


def inspect(port: int, as_json: bool) -> int:
    """Show the processes on ``port``, with a menu of actions in an interactive terminal."""
    listeners = _find(port)
    if as_json:
        _print_json([listener.to_dict() for listener in listeners])
    elif _identified(port, listeners):
        url, log = net.web_url(port), _log_file(listeners)
        ui.console.print(ui.listener_panel(port, listeners, url, log))
        if sys.stdin.isatty() and sys.stdout.isatty():
            _menu(port, listeners, url, log)
    return OK if listeners else FAILURE


def kill(port: int, confirm: bool = True) -> int:
    """Stop the processes listening on ``port``, asking first unless ``confirm`` is False."""
    listeners = _find(port)
    if not _identified(port, listeners):
        return FAILURE
    if confirm:
        if not Confirm.ask(Text(f"Kill {_labels(listeners)}?"), default=False):
            return FAILURE
        # Answering can take a while: only stop processes that are still on the port
        still_listening = {listener.pid for listener in discovery.find_listeners(port)}
        listeners = [listener for listener in listeners if listener.pid in still_listening]
        if not listeners:
            ui.warning(f"Port {port} changed while waiting for your answer; nothing was stopped.")
            return FAILURE

    stuck = processes.terminate(listener.pid for listener in listeners if listener.pid is not None)
    if stuck:
        ui.error(f"Couldn't stop PID {', '.join(map(str, stuck))}.")
        _privilege_tip()
        return FAILURE
    ui.success(f"Stopped {_labels(listeners)}.")
    return OK


def copy(port: int) -> int:
    listeners = _find(port)
    return _copy(listeners) if _identified(port, listeners) else FAILURE


def open_in_browser(port: int) -> int:
    url = net.web_url(port)
    if url is None:
        ui.error(f"No web server is answering on port {port}.")
        return FAILURE
    return _open(url)


def watch(port: int) -> int:
    """Report processes starting and stopping on ``port`` until interrupted."""
    ui.info(f"Watching port {port}. Press Ctrl+C to stop.")
    previous: dict[int | None, Listener] | None = None
    with contextlib.suppress(KeyboardInterrupt):
        for listeners in _changes(port):
            current = {listener.pid: listener for listener in listeners}
            if previous is None:
                ui.event(f"in use by {_labels(listeners)}" if listeners else "free")
            else:
                for pid in previous.keys() - current.keys():
                    ui.event(f"stopped: {ui.label(previous[pid])}")
                for pid in current.keys() - previous.keys():
                    ui.event(f"started: {ui.label(current[pid])}")
            previous = current
    return OK


def notify(port: int) -> int:
    """Wait until something listens on ``port``, then send a desktop notification."""
    ui.info(f"Waiting for port {port} to be used. Press Ctrl+C to stop.")
    listeners = next(found for found in _changes(port) if found)
    ui.success(f"Port {port} is in use by {_labels(listeners)}.")
    if not system.notify(f"Port {port} is in use", _labels(listeners)):
        ui.warning("Couldn't show a desktop notification.")
    return OK


def stats(port: int | None, as_json: bool) -> int:
    """Show the ports seen most often, or the history of one port."""
    store = StatsStore()
    if port is not None:
        record = store.port(port)
        if as_json:
            _print_json(None if record is None else asdict(record))
        elif record is None:
            ui.info(f"wtfport hasn't seen port {port} in use yet.")
        else:
            ui.console.print(ui.port_history(record))
        return OK if record else FAILURE

    ports, seen = store.ports(), store.processes()
    if as_json:
        _print_json(
            {
                "last_updated": store.last_updated,
                "ports": [asdict(record) for record in ports],
                "processes": [asdict(record) for record in seen],
            }
        )
    elif store.last_updated is None:
        ui.info("No history yet. It builds up as you use wtfport.")
    else:
        ui.console.print(ui.stats_summary(ports, seen, store.last_updated))
        ui.tip("Run `wtfport <port> --stats` for the history of one port.")
    return OK


def debug() -> int:
    """Print details about the environment, for bug reports."""
    ui.console.print(
        ui.key_values(
            {
                "wtfport": __version__,
                "Python": f"{platform.python_version()} ({sys.executable})",
                "Platform": platform.platform(),
                "User": _current_user(),
                "Elevated": "yes" if system.is_admin() else "no",
                "lsof": discovery.lsof_path() or "not found",
                "History file": str(default_path()),
            }
        )
    )
    return OK


def _remember(listeners: list[Listener]) -> list[Listener]:
    """Add the listeners to the port history, and pass them through."""
    StatsStore().record(listeners)
    return listeners


def _find(port: int) -> list[Listener]:
    return _remember(discovery.find_listeners(port))


def _changes(port: int) -> Iterator[list[Listener]]:
    """Yield the listeners on ``port`` now, then again each time the set of processes changes."""
    previous: set[int | None] | None = None
    while True:
        listeners = discovery.find_listeners(port)
        pids = {listener.pid for listener in listeners}
        if pids != previous:
            yield _remember(listeners)
            previous = pids
        time.sleep(POLL_INTERVAL)


def _identified(port: int, listeners: list[Listener]) -> bool:
    """Return True if there's a known process on the port; otherwise explain why not."""
    if not listeners:
        ui.info(f"Nothing is listening on port {port}.")
        return False
    if listeners[0].pid is None:
        ui.warning(f"Port {port} is in use, but you can't see which process owns it.")
        _privilege_tip()
        return False
    return True


def _menu(port: int, listeners: list[Listener], url: str | None, log: Path | None) -> None:
    options: dict[str, tuple[str, Callable[[], int]]] = {}
    if url is not None:
        options["o"] = ("Open in browser", partial(_open, url))
    options["k"] = ("Kill", partial(kill, port))
    options["c"] = ("Copy command", partial(_copy, listeners))
    if log is not None:
        options["l"] = ("Follow log", partial(_follow, log))

    ui.console.print(ui.menu({key: text for key, (text, _) in options.items()} | {"q": "Quit"}))
    while (choice := _choose([*options, "q"])) != "q":
        _, run = options[choice]
        if run() == OK and choice == "k":
            return  # nothing left to act on


def _choose(choices: list[str]) -> str:
    return Prompt.ask("Choose", choices=choices, default="q", case_sensitive=False)


def _copy(listeners: list[Listener]) -> int:
    command = next((listener.command for listener in listeners if listener.command), None)
    if command is None:
        ui.error("The process's command line isn't visible to you.")
        _privilege_tip()
        return FAILURE
    if not system.copy_to_clipboard(command):
        ui.error("Couldn't access the clipboard. On Linux, install wl-clipboard, xclip or xsel.")
        return FAILURE
    ui.success("Copied the command to the clipboard.")
    return OK


def _open(url: str) -> int:
    if not webbrowser.open(url):
        ui.error(f"Couldn't open a browser for {url}.")
        return FAILURE
    ui.success(f"Opened {url}")
    return OK


def _follow(log: Path) -> int:
    ui.info(f"Following {log}. Press Ctrl+C to stop.")
    try:
        for line in logs.follow(log):
            ui.console.out(line.rstrip("\n"), highlight=False)
    except KeyboardInterrupt:
        pass
    except OSError as exc:
        ui.error(f"Stopped following {log}: {exc.strerror or exc}")
        return FAILURE
    return OK


def _log_file(listeners: Iterable[Listener]) -> Path | None:
    for listener in listeners:
        if listener.pid is not None and (log := logs.find_log_file(listener.pid)):
            return log
    return None


def _labels(listeners: Iterable[Listener]) -> str:
    return ", ".join(ui.label(listener) for listener in listeners)


def _privilege_tip() -> None:
    if not system.is_admin():
        how = "as Administrator" if sys.platform == "win32" else "with sudo"
        ui.tip(f"Processes owned by other users may be hidden; run {how} to see them.")


def _current_user() -> str:
    try:
        return getpass.getuser()
    except (OSError, KeyError):  # no login name, e.g. an arbitrary uid in a container
        return "unknown"


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2))
