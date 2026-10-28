import pytest

from wtfport import actions
from wtfport.models import Listener

LISTENERS = [Listener(3000, 1, "node", "node server.js")]


@pytest.fixture
def stopped(monkeypatch) -> list[int]:
    """Pids passed to processes.terminate, which pretends they all stopped."""
    pids: list[int] = []
    monkeypatch.setattr(actions.processes, "terminate", lambda found: pids.extend(found) or [])
    return pids


def answer(monkeypatch, confirmed: bool) -> None:
    monkeypatch.setattr(actions.Confirm, "ask", lambda *args, **kwargs: confirmed)


def on_port(monkeypatch, *results: list[Listener]) -> None:
    """Make successive discovery lookups return ``results`` in order."""
    remaining = iter(results)
    monkeypatch.setattr(actions.discovery, "find_listeners", lambda port: next(remaining))


def choose(monkeypatch, *choices: str) -> list[list[str]]:
    """Make the menu prompt return ``choices`` in order; returns the options offered each time."""
    offered: list[list[str]] = []
    answers = iter(choices)

    def fake_choose(options):
        offered.append(options)
        return next(answers)

    monkeypatch.setattr(actions, "_choose", fake_choose)
    return offered


def test_kill_after_confirmation(monkeypatch, stopped):
    on_port(monkeypatch, LISTENERS, LISTENERS)
    answer(monkeypatch, confirmed=True)

    assert actions.kill(3000) == actions.OK
    assert stopped == [1]


def test_kill_declined(monkeypatch, stopped):
    on_port(monkeypatch, LISTENERS)
    answer(monkeypatch, confirmed=False)

    assert actions.kill(3000) == actions.FAILURE
    assert stopped == []


def test_kill_skips_processes_replaced_while_confirming(monkeypatch, stopped):
    on_port(monkeypatch, LISTENERS, [Listener(3000, 2, "node")])
    answer(monkeypatch, confirmed=True)

    assert actions.kill(3000) == actions.FAILURE
    assert stopped == []


def test_kill_invisible_owner(monkeypatch, stopped):
    on_port(monkeypatch, [Listener(3000)])

    assert actions.kill(3000, confirm=False) == actions.FAILURE
    assert stopped == []


def test_menu_offers_only_available_actions(monkeypatch):
    offered = choose(monkeypatch, "q")

    actions._menu(3000, LISTENERS, url=None, log=None)

    assert offered == [["k", "c", "q"]]


def test_menu_runs_actions_until_quit(monkeypatch, tmp_path):
    copied = []
    monkeypatch.setattr(
        actions.system, "copy_to_clipboard", lambda text: copied.append(text) or True
    )
    offered = choose(monkeypatch, "c", "c", "q")

    actions._menu(3000, LISTENERS, url="http://localhost:3000", log=tmp_path / "app.log")

    assert offered[0] == ["o", "k", "c", "l", "q"]
    assert copied == ["node server.js", "node server.js"]


def test_menu_closes_after_successful_kill(monkeypatch, stopped):
    on_port(monkeypatch, LISTENERS, LISTENERS)
    answer(monkeypatch, confirmed=True)
    offered = choose(monkeypatch, "k")

    actions._menu(3000, LISTENERS, url=None, log=None)

    assert len(offered) == 1
    assert stopped == [1]


def test_menu_stays_open_when_kill_is_declined(monkeypatch, stopped):
    on_port(monkeypatch, LISTENERS)
    answer(monkeypatch, confirmed=False)
    offered = choose(monkeypatch, "k", "q")

    actions._menu(3000, LISTENERS, url=None, log=None)

    assert len(offered) == 2
