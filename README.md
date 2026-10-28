# wtfport

Find out what's using a port, then inspect, kill, or watch it.

```
$ wtfport 3000
╭─ Port 3000 ─────────────────────────────╮
│                                         │
│  Process  node                          │
│  PID      1234                          │
│  Command  node server.js                │
│  User     you                           │
│  Started  3m ago                        │
│  URL      http://localhost:3000         │
│                                         │
╰─────────────────────────────────────────╯
o  Open in browser
k  Kill
c  Copy command
q  Quit
```

Works on macOS, Linux and Windows with Python 3.10+.

## Install

```bash
pipx install wtfport
```

## Usage

```bash
wtfport                  # list every listening port
wtfport 3000             # inspect port 3000
wtfport 3000 --kill      # stop the process on port 3000 (--yes to skip the prompt)
wtfport 3000 --copy      # copy its command line
wtfport 3000 --open      # open it in your browser
wtfport 3000 --watch     # report processes starting and stopping
wtfport 3000 --notify    # get a desktop notification when it's in use
wtfport 3000 --stats     # how often you've seen it, and by what (--stats alone for all ports)
```

Run `wtfport --help` for every option.

## Scripting

`--json` prints a list of listeners for lookups and listings:

```bash
$ wtfport 3000 --json
[
  {
    "port": 3000,
    "pid": 1234,
    "name": "node",
    "command": "node server.js",
    "user": "you",
    "started_at": "2026-10-28T14:30:22+01:00"
  }
]
```

Exit codes: `0` success, `1` nothing listening or the action failed, `2` invalid usage, `130` interrupted. So `wtfport 3000 --json > /dev/null || npm start` starts a server only if the port is free.

Without `sudo` (or Administrator on Windows), other users' processes show up with unknown details, and on macOS they're missing from the full listing.

## Privacy

Everything runs locally. Port history is kept in `~/.wtfport/stats.json`; delete it to start over.

## Development

```bash
pip install -e . --group dev
ruff format --check . && ruff check . && mypy && pytest
```

## License

MIT, by [Hungwa Henry](https://github.com/hungwahenry).
