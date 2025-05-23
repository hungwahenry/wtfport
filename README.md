# wtfport

A terminal-based tool that provides developers with an intuitive, human-friendly way to identify, inspect, and interact with processes bound to specific ports on their system.

![wtfport demo](https://raw.githubusercontent.com/hungwahenry/wtfport/main/docs/demo.gif)

## Features

- **Port Lookup**: Quickly show details about the process using a specific port
- **Process Management**: Kill a process running on a port with a simple command
- **Cross-Platform Support**: Available for macOS, Linux, and Windows
- **Colorized Output**: Clear, visually appealing terminal output
- **Watch Mode**: Continuously monitor and update port usage
- **Interactive Mode**: Simple interface for interacting with processes
- **Clipboard Support**: Copy process commands directly to clipboard
- **Web Server Detection**: Quick access to open web servers in browser
- **Log Tailing**: Ability to detect and tail logs for processes
- **Port Statistics**: Track and analyze your most frequently used ports
- **Notifications**: Get alerted when a specific port becomes active

## Installation

### Using pip

```bash
pip install wtfport
```

### Using Homebrew (macOS/Linux)

```bash
brew install wtfport
```

### From Source

```bash
git clone https://github.com/hungwahenry/wtfport.git
cd wtfport
pip install -e .
```

## Usage

### Basic Commands

Check a specific port:
```bash
wtfport 3000
```

Show all listening ports:
```bash
wtfport
# or
wtfport --all
```

Kill a process on a port:
```bash
wtfport 3000 --kill
```

### Monitoring Features

Watch a port for changes:
```bash
wtfport 3000 --watch
```

Get notified when a port becomes active:
```bash
wtfport --notify 5000
```

### For Web Developers

Open a web server in browser:
```bash
wtfport 3000 --open
```

### Port Statistics and History

View port usage statistics:
```bash
wtfport --stats
```

View detailed history for a specific port:
```bash
wtfport --stats-detail 3000
```

### Automation & Scripting

Get JSON output for scripting:
```bash
wtfport 3000 --json
```

Copy the command to clipboard:
```bash
wtfport 3000 --copy
```

### Interactive Mode

When running `wtfport <port>` without additional flags, you'll enter interactive mode where you can:

- Open the port in a browser
- Kill the process
- Copy the command to clipboard
- Tail logs (if available)

## Examples

### Finding What's Using a Port

```bash
$ wtfport 3000

Port 3000 is being used by:
╭──────────────────────────────────────────────────────────────────╮
│                                                                  │
│ ✓ Process:   node                                                │
│    PID:       1234                                               │
│    Command:   node server.js                                     │
│    User:      yourname                                           │
│    Started:   3m ago                                             │
│                                                                  │
╰──────────────────────────────────────────────────────────────────╯

Options:
[O] Open in browser      (http://localhost:3000)
[K] Kill process         (sudo may be required)
[C] Copy command         (to clipboard)
[Q] Quit
```

### Viewing All Listening Ports

```bash
$ wtfport

Listening Ports:
┏━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃  Port ┃ Process       ┃   PID ┃ User      ┃ Started     ┃
┡━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│   22  │ sshd          │   122 │ root      │ 4h ago      │
│  443  │ httpd         │   436 │ www       │ 2d ago      │
│ 3000  │ node          │  1234 │ yourname  │ 3m ago      │
│ 5432  │ postgres      │   983 │ postgres  │ 2d ago      │
└───────┴───────────────┴───────┴───────────┴─────────────┘

Tip: run `wtfport <port>` to inspect in detail.
```

### Port Statistics

```bash
$ wtfport --stats

Port Usage Statistics:

Tracking data for 15 ports and 7 processes.
Last updated: 2023-06-15T14:30:22.456789

Top Ports:
┏━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃  Port ┃ Access Count ┃ Processes                  ┃ Last Seen    ┃
┡━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ 3000  │ 42           │ node, python, ruby         │ 2023-06-15   │
│ 8080  │ 27           │ java, tomcat               │ 2023-06-14   │
│ 5432  │ 18           │ postgres                   │ 2023-06-15   │
│ 443   │ 15           │ nginx, apache              │ 2023-06-15   │
│ 27017 │ 10           │ mongod                     │ 2023-06-13   │
└───────┴──────────────┴────────────────────────────┴──────────────┘

Top Processes:
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Process   ┃ Access Count ┃ Used Ports                       ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ node      │ 45           │ 3000, 8000, 9000, 4200, 4000     │
│ postgres  │ 18           │ 5432                             │
│ nginx     │ 15           │ 443, 80                          │
│ java      │ 12           │ 8080, 8443                       │
│ mongod    │ 10           │ 27017                            │
└───────────┴──────────────┴─────────────────────────────────┘

Tip: Use `wtfport --stats-detail <port>` to see detailed history for a specific port.
```

## Requirements

- Python 3.7 or higher
- Dependencies (automatically installed):
  - typer
  - rich
  - psutil
  - pyperclip

## Privacy

wtfport runs completely locally on your machine. The statistics feature stores data only in a local file (~/.wtfport/stats.json) and no data is ever sent outside your computer.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

Created by [Hungwa Henry](https://github.com/hungwahenry)
