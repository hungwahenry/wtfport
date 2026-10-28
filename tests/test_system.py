import pytest

from wtfport import system


@pytest.fixture
def commands(monkeypatch) -> list[tuple[list[str], bytes | None, dict[str, str] | None]]:
    """Commands system would run, recorded instead of run; they all succeed."""
    calls: list[tuple[list[str], bytes | None, dict[str, str] | None]] = []

    def fake_run(command, stdin=None, env=None):
        calls.append((command, stdin, env))
        return True

    monkeypatch.setattr(system, "_run", fake_run)
    return calls


def on(monkeypatch, platform: str, installed: tuple[str, ...] = ()) -> None:
    monkeypatch.setattr(system.sys, "platform", platform)
    monkeypatch.setattr(system.shutil, "which", lambda name: name if name in installed else None)


def test_linux_clipboard_uses_first_available_tool(monkeypatch, commands):
    on(monkeypatch, "linux", installed=("xsel",))

    assert system.copy_to_clipboard("node café.js")
    assert commands == [(["xsel", "--clipboard", "--input"], "node café.js".encode(), None)]


def test_linux_clipboard_without_tools(monkeypatch, commands):
    on(monkeypatch, "linux")

    assert not system.copy_to_clipboard("node server.js")
    assert commands == []


def test_windows_clipboard_passes_text_through_environment(monkeypatch, commands):
    on(monkeypatch, "win32")

    assert system.copy_to_clipboard("node café.js")
    ((command, _, env),) = commands
    assert command[0] == "powershell"
    assert env == {"WTFPORT_TEXT": "node café.js"}


def test_macos_notification_text_is_passed_as_arguments(monkeypatch, commands):
    on(monkeypatch, "darwin")

    system.notify('Port "3000"', "node & friends")

    ((command, _, _),) = commands
    assert command[0] == "osascript"
    assert command[-2:] == ['Port "3000"', "node & friends"]


def test_windows_notification_script_is_bundled(monkeypatch, commands):
    on(monkeypatch, "win32")

    system.notify("title", "message")

    ((command, _, env),) = commands
    assert "ToastNotificationManager" in command[-1]
    assert env == {"WTFPORT_TITLE": "title", "WTFPORT_MESSAGE": "message"}


def test_failed_command_reports_false():
    assert not system._run(["wtfport-no-such-command"])
