# Changelog

## Unreleased

### Fixed

- Following a log with Windows line endings no longer leaves a carriage return at the end of each line.

## 0.2.0 - 2026-10-29

A rewrite. 0.1.x couldn't start after installation, so this is effectively the first working release.

### Fixed

- `pip install wtfport` installs a working tool. 0.1.x declared `click` instead of `typer` and `rich`, and pointed the `wtfport` command at the wrong function, so it either crashed or ignored its arguments.
- Options can follow the port number (`wtfport 3000 --kill`).
- Killing only targets processes listening on the port. The old force-kill fallback could also kill unrelated programs that were merely connected to that port number elsewhere.
- Ports owned by other users are reported as "in use, owner not visible" instead of being attributed to wtfport itself.
- Servers listening only on IPv6 (`::1`), as many Node dev servers do on macOS, are detected.
- Process names are no longer truncated on macOS, and names containing square brackets display correctly.
- `--stats` records real process names (it recorded "unknown" for listings).
- Notification text can't be interpreted as AppleScript or PowerShell, and the Windows notification script no longer passes the wrong object to the notifier.
- On Windows, `--copy` uses PowerShell's `Set-Clipboard` instead of `clip.exe`, which garbles text outside the console code page.

### Changed

- `--notify` and `--stats` use the PORT argument like every other action: `wtfport 5000 --notify` instead of `wtfport --notify 5000`, and `wtfport 3000 --stats` instead of `wtfport --stats-detail 3000`.
- Conflicting flags (such as `--kill --watch`) are rejected instead of silently ignored, and exit codes are meaningful: 0 for success, 1 for not found or failed, 2 for invalid usage.
- `--json` output is a list of listeners with one consistent set of fields, for lookups and listings alike.
- `--kill` stops every process listening on the port (e.g. all workers of a pre-forking server), not just the first.
- Log detection looks at the files a process actually has open, instead of guessing from its command line, and following a log survives truncation and rotation.
- Port detection for `--open` asks plain HTTP first, so dev servers don't log a garbled request every time you inspect them.
- The interactive menu only appears in a terminal, so piping `wtfport 3000` no longer waits for input.
- Requires Python 3.10 or newer.

### Added

- `--yes` to skip the `--kill` confirmation in scripts.
- HTTPS detection for `--open` and the interactive menu.
- `python -m wtfport`.
- A small Python API: `find_listeners`, `list_listeners`, `terminate` and `Listener`, with type hints.

### Removed

- `--examples`, which repeated the examples now shown by `--help`.
- `--stats-detail`, replaced by `wtfport <port> --stats`.
- The optional `pyperclip` and `plyer` integrations; the built-in system tools cover the same platforms.

## 0.1.1 - 2025-04-12

- Packaging fixes.

## 0.1.0 - 2025-04-12

- Initial release.
