import os
import subprocess

import psutil

from wtfport import discovery
from wtfport.models import Listener

LSOF_OUTPUT = "p123\nf3\nn*:3000\nf4\nn[::1]:3000\np456\nf5\nn127.0.0.1:8080\n"


def test_finds_own_listener(listening_port):
    (listener,) = discovery.find_listeners(listening_port)

    assert listener.port == listening_port
    assert listener.pid == os.getpid()
    assert listener.name
    assert listener.command
    assert listener.started_at is not None


def test_lists_own_listener(listening_port):
    assert (listening_port, os.getpid()) in {
        (listener.port, listener.pid) for listener in discovery.list_listeners()
    }


def test_free_port_has_no_listeners(free_port):
    assert discovery.find_listeners(free_port) == []


def denied(kind):
    raise psutil.AccessDenied()


def test_open_port_without_visible_owner(monkeypatch, listening_port):
    # As on macOS without root: no socket table, and lsof can't see the owner
    monkeypatch.setattr(discovery.psutil, "net_connections", denied)
    monkeypatch.setattr(discovery, "_run_lsof", lambda port: "")

    assert discovery.find_listeners(listening_port) == [Listener(listening_port)]


def test_anonymous_socket_dropped_when_owner_is_known(monkeypatch):
    sockets = {(5000, None), (5000, os.getpid()), (6000, None)}
    monkeypatch.setattr(discovery, "_listening_sockets", lambda port=None: sockets)

    listeners = discovery.list_listeners()

    assert [(listener.port, listener.pid) for listener in listeners] == [
        (5000, os.getpid()),
        (6000, None),
    ]


def test_skips_processes_that_exited(monkeypatch):
    def gone(pid):
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr(discovery, "_listening_sockets", lambda port=None: {(5000, 123)})
    monkeypatch.setattr(discovery.psutil, "Process", gone)

    assert discovery.list_listeners() == []


def test_falls_back_to_lsof_without_socket_table_access(monkeypatch):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=LSOF_OUTPUT, stderr="")

    monkeypatch.setattr(discovery.psutil, "net_connections", denied)
    monkeypatch.setattr(discovery, "lsof_path", lambda: "/usr/sbin/lsof")
    monkeypatch.setattr(discovery.subprocess, "run", fake_run)

    assert discovery._listening_sockets(3000) == {(3000, 123), (8080, 456)}
    assert "-iTCP:3000" in commands[0]
    assert "-sTCP:LISTEN" in commands[0]


def test_lsof_missing(monkeypatch):
    monkeypatch.setattr(discovery, "lsof_path", lambda: None)

    assert discovery._run_lsof(None) == ""


def test_lsof_failure(monkeypatch):
    def hang(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(discovery, "lsof_path", lambda: "/usr/sbin/lsof")
    monkeypatch.setattr(discovery.subprocess, "run", hang)

    assert discovery._run_lsof(3000) == ""


def test_lsof_found_outside_path(monkeypatch):
    searched = []

    def which(name, path=None):
        searched.append(path)
        return None if path is None else "/usr/sbin/lsof"

    monkeypatch.setattr(discovery.shutil, "which", which)

    assert discovery.lsof_path() == "/usr/sbin/lsof"
    assert "/usr/sbin" in searched[1]


def test_command_is_shell_quoted():
    command = discovery._join_command(["node", "my server.js"])

    assert command in ("node 'my server.js'", 'node "my server.js"')
