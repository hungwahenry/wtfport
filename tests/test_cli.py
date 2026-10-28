import json
import os
import subprocess
import sys
from importlib.metadata import entry_points

import pytest
from typer.testing import CliRunner

from wtfport import __version__, actions, cli, system
from wtfport.models import Listener

runner = CliRunner()


def run(*args: str):
    return runner.invoke(cli.app, list(args))


def test_console_script_points_at_app():
    (entry_point,) = entry_points(group="console_scripts", name="wtfport")
    assert entry_point.load() is cli.app


def test_runs_as_module():
    result = subprocess.run(
        [sys.executable, "-m", "wtfport", "--version"], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == f"wtfport {__version__}"


def test_version():
    result = run("--version")
    assert result.exit_code == 0
    assert __version__ in result.output


def test_inspect_json(listening_port):
    result = run(str(listening_port), "--json")

    assert result.exit_code == 0, result.output
    (listener,) = json.loads(result.stdout)
    assert listener["port"] == listening_port
    assert listener["pid"] == os.getpid()


def test_inspect_free_port(free_port):
    result = run(str(free_port))
    assert result.exit_code == 1
    assert f"Nothing is listening on port {free_port}" in result.output

    result = run(str(free_port), "--json")
    assert result.exit_code == 1
    assert json.loads(result.stdout) == []


def test_inspect_shows_details_without_prompting(listening_port):
    result = run(str(listening_port))

    assert result.exit_code == 0, result.output
    assert str(os.getpid()) in result.output
    assert "Choose" not in result.output


def test_list_json_includes_listener(listening_port):
    result = run("--all", "--json")

    assert result.exit_code == 0, result.output
    assert listening_port in [listener["port"] for listener in json.loads(result.stdout)]


def test_kill(server):
    process, port = server

    result = run(str(port), "--kill", "--yes")

    assert result.exit_code == 0, result.output
    assert process.wait(timeout=5) is not None


def test_kill_declined_leaves_process_running(server):
    process, port = server

    result = runner.invoke(cli.app, [str(port), "--kill"], input="n\n")

    assert result.exit_code == 1
    assert process.poll() is None


def test_copy(monkeypatch, listening_port):
    copied = []
    monkeypatch.setattr(system, "copy_to_clipboard", lambda text: copied.append(text) or True)

    result = run(str(listening_port), "--copy")

    assert result.exit_code == 0, result.output
    assert copied and "python" in copied[0].lower()


def test_open(monkeypatch, http_port):
    opened = []
    monkeypatch.setattr(actions.webbrowser, "open", lambda url: opened.append(url) or True)

    result = run(str(http_port), "--open")

    assert result.exit_code == 0, result.output
    assert opened == [f"http://localhost:{http_port}"]


def test_open_without_web_server(listening_port, monkeypatch):
    monkeypatch.setattr(actions.net, "web_url", lambda port: None)

    assert run(str(listening_port), "--open").exit_code == 1


def test_notify_when_port_is_in_use(monkeypatch, listening_port):
    notifications = []
    monkeypatch.setattr(system, "notify", lambda *args: notifications.append(args) or True)

    result = run(str(listening_port), "--notify")

    assert result.exit_code == 0, result.output
    assert notifications[0][0] == f"Port {listening_port} is in use"


def test_watch_reports_changes(monkeypatch):
    states = iter([[], [Listener(3000, 1, "node")], [Listener(3000, 2, "deno")]])

    def find_listeners(port):
        try:
            return next(states)
        except StopIteration:
            raise KeyboardInterrupt from None

    monkeypatch.setattr(actions.discovery, "find_listeners", find_listeners)
    monkeypatch.setattr(actions.time, "sleep", lambda seconds: None)

    result = run("3000", "--watch")

    assert result.exit_code == 0, result.output
    lines = [line.split("  ", 1)[1] for line in result.output.splitlines()[1:]]
    assert lines == [
        "free",
        "started: node (PID 1)",
        "stopped: node (PID 1)",
        "started: deno (PID 2)",
    ]


def test_stats_after_lookup(listening_port):
    run(str(listening_port), "--json")

    summary = json.loads(run("--stats", "--json").stdout)
    history = json.loads(run(str(listening_port), "--stats", "--json").stdout)

    assert listening_port in [record["port"] for record in summary["ports"]]
    assert history["count"] == 1
    assert history["processes"]


def test_stats_for_unseen_port():
    assert run("1234", "--stats").exit_code == 1


def test_debug():
    result = run("--debug")
    assert result.exit_code == 0
    assert __version__ in result.output


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["3000", "--kill", "--watch"], "can't be used together"),
        (["--kill"], "needs a PORT"),
        (["3000", "--all"], "doesn't take a PORT"),
        (["3000", "--kill", "--json"], "--json can't be used with --kill"),
        (["3000", "--yes"], "--yes only applies to --kill"),
        (["70000"], "range"),
    ],
)
def test_invalid_usage(args, message):
    result = run(*args)

    assert result.exit_code == 2
    assert message in result.output
