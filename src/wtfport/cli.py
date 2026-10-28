"""Command-line interface: parses options, checks they make sense together, and dispatches."""

from typing import Annotated

import typer

from wtfport import __version__, actions

EXAMPLES = "\n\n".join(
    [
        "[bold]Examples[/]",
        "wtfport                  list every listening port",
        "wtfport 3000             inspect port 3000 (with a menu in a terminal)",
        "wtfport 3000 --kill      stop the process on port 3000",
        "wtfport 3000 --watch     report processes starting and stopping on port 3000",
        "wtfport 5000 --notify    get a desktop notification when port 5000 is in use",
        "wtfport --stats          show the ports you've seen most often",
        "wtfport 3000 --json      print JSON for scripts",
    ]
)

# Actions that can print JSON; None is the default lookup or listing
JSON_FLAGS = (None, "--all", "--stats")

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"wtfport {__version__}")
        raise typer.Exit()


@app.command(epilog=EXAMPLES)
def main(
    ctx: typer.Context,
    port: Annotated[
        int | None,
        typer.Argument(
            min=1,
            max=65535,
            metavar="PORT",
            show_default=False,
            help="Port to inspect. Without it, every listening port is listed.",
        ),
    ] = None,
    show_all: Annotated[
        bool, typer.Option("--all", "-a", help="List every listening port.")
    ] = False,
    kill: Annotated[
        bool, typer.Option("--kill", "-k", help="Stop the process listening on PORT.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Don't ask before --kill stops anything.")
    ] = False,
    copy: Annotated[
        bool, typer.Option("--copy", "-c", help="Copy the command of PORT's process.")
    ] = False,
    open_: Annotated[
        bool, typer.Option("--open", "-o", help="Open PORT in a web browser.")
    ] = False,
    watch: Annotated[
        bool, typer.Option("--watch", "-w", help="Report processes starting and stopping.")
    ] = False,
    notify: Annotated[
        bool, typer.Option("--notify", "-n", help="Notify when something listens on PORT.")
    ] = False,
    stats: Annotated[
        bool, typer.Option("--stats", "-s", help="Show the ports seen most, or PORT's history.")
    ] = False,
    as_json: Annotated[
        bool, typer.Option("--json", "-j", help="Print JSON. Works with listings and --stats.")
    ] = False,
    debug: Annotated[
        bool, typer.Option("--debug", "-d", help="Print environment details for bug reports.")
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version", "-v", callback=_print_version, is_eager=True, help="Show the version."
        ),
    ] = False,
) -> None:
    """Find out what's using a port, then inspect, kill, or watch it."""
    flags = {
        "--all": show_all,
        "--kill": kill,
        "--copy": copy,
        "--open": open_,
        "--watch": watch,
        "--notify": notify,
        "--stats": stats,
        "--debug": debug,
    }
    chosen = [flag for flag, enabled in flags.items() if enabled]
    if len(chosen) > 1:
        ctx.fail(f"{chosen[0]} and {chosen[1]} can't be used together.")
    flag = chosen[0] if chosen else None
    if yes and flag != "--kill":
        ctx.fail("--yes only applies to --kill.")
    if as_json and flag not in JSON_FLAGS:
        ctx.fail(f"--json can't be used with {flag}.")

    match flag:
        case None:
            code = actions.show_all(as_json) if port is None else actions.inspect(port, as_json)
        case "--all":
            _reject_port(ctx, flag, port)
            code = actions.show_all(as_json)
        case "--debug":
            _reject_port(ctx, flag, port)
            code = actions.debug()
        case "--stats":
            code = actions.stats(port, as_json)
        case "--kill":
            code = actions.kill(_require_port(ctx, flag, port), confirm=not yes)
        case "--copy":
            code = actions.copy(_require_port(ctx, flag, port))
        case "--open":
            code = actions.open_in_browser(_require_port(ctx, flag, port))
        case "--watch":
            code = actions.watch(_require_port(ctx, flag, port))
        case "--notify":
            code = actions.notify(_require_port(ctx, flag, port))
        case _:
            raise AssertionError(f"unhandled flag {flag}")
    raise typer.Exit(code)


def _require_port(ctx: typer.Context, flag: str, port: int | None) -> int:
    if port is None:
        ctx.fail(f"{flag} needs a PORT, for example: wtfport 3000 {flag}")
    return port


def _reject_port(ctx: typer.Context, flag: str, port: int | None) -> None:
    if port is not None:
        ctx.fail(f"{flag} doesn't take a PORT.")
