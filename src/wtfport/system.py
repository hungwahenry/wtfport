"""Operating-system integration: privileges, clipboard and desktop notifications."""

import os
import shutil
import subprocess
import sys
from importlib import resources

POWERSHELL = ["powershell", "-NoProfile", "-NonInteractive", "-Command"]
LINUX_CLIPBOARDS = [
    ["wl-copy"],
    ["xclip", "-selection", "clipboard"],
    ["xsel", "--clipboard", "--input"],
]

# Notification text is passed as arguments so it is never interpreted as AppleScript
MACOS_NOTIFY = """on run argv
display notification (item 2 of argv) with title (item 1 of argv)
end run"""


def is_admin() -> bool:
    """Return True when running as root or an elevated Windows administrator."""
    if sys.platform == "win32":
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    return os.geteuid() == 0


def copy_to_clipboard(text: str) -> bool:
    """Copy ``text`` to the system clipboard; returns False if no clipboard tool works."""
    if sys.platform == "win32":
        # clip.exe would garble anything outside the console code page
        return _run(
            [*POWERSHELL, "Set-Clipboard -Value $env:WTFPORT_TEXT"], env={"WTFPORT_TEXT": text}
        )
    commands = [["pbcopy"]] if sys.platform == "darwin" else LINUX_CLIPBOARDS
    return any(
        shutil.which(command[0]) is not None and _run(command, stdin=text.encode())
        for command in commands
    )


def notify(title: str, message: str) -> bool:
    """Show a desktop notification; returns False if it couldn't be shown."""
    if sys.platform == "darwin":
        return _run(["osascript", "-e", MACOS_NOTIFY, title, message])
    if sys.platform == "win32":
        script = resources.files("wtfport").joinpath("notify.ps1").read_text(encoding="utf-8")
        return _run([*POWERSHELL, script], env={"WTFPORT_TITLE": title, "WTFPORT_MESSAGE": message})
    return _run(["notify-send", "--app-name=wtfport", title, message])


def _run(command: list[str], stdin: bytes | None = None, env: dict[str, str] | None = None) -> bool:
    """Run ``command`` with ``env`` added to the environment; return whether it succeeded."""
    try:
        # Output goes to DEVNULL, not a pipe: xclip and wl-copy fork a daemon that keeps
        # inherited pipes open, which would block until the timeout
        subprocess.run(
            command,
            input=stdin,
            env=None if env is None else {**os.environ, **env},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True
