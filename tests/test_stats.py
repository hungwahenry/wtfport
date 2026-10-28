import sys

import pytest

from wtfport import stats
from wtfport.models import Listener
from wtfport.stats import StatsStore, default_path


def test_records_ports_and_processes(home):
    store = StatsStore()
    store.record(
        [Listener(3000, 1, "node"), Listener(3000, 2, "node"), Listener(5432, 3, "postgres")]
    )
    store.record([Listener(3000, 1, "node")])

    reloaded = StatsStore()
    assert default_path().parent == home / ".wtfport"
    assert [(r.port, r.count, r.processes) for r in reloaded.ports()] == [
        (3000, 2, ("node",)),
        (5432, 1, ("postgres",)),
    ]
    assert [(r.name, r.count, r.ports) for r in reloaded.processes()] == [
        ("node", 2, (3000,)),
        ("postgres", 1, (5432,)),
    ]


def test_anonymous_listener_counts_the_port_only():
    store = StatsStore()
    store.record([Listener(22)])

    assert store.port(22) is not None
    assert store.processes() == []


def test_unknown_port():
    assert StatsStore().port(1234) is None


def test_recording_nothing_writes_nothing():
    StatsStore().record([])

    assert not default_path().exists()


def test_corrupt_file_starts_fresh():
    default_path().parent.mkdir()
    default_path().write_text("{not json")

    store = StatsStore()
    assert store.ports() == []
    store.record([Listener(8080, 1, "java")])
    assert StatsStore().port(8080) is not None


def test_unwritable_location_is_ignored(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("")

    StatsStore(blocker / "stats.json").record([Listener(80, 1, "nginx")])


@pytest.mark.parametrize(
    "content",
    [
        '{"version": 1}',
        "[]",
        '"text"',
        '{"version": 1, "ports": {"x": {}}, "processes": {}, "last_updated": null}',
        '{"version": 1, "ports": {"80": {"count": "many"}}, "processes": {}, "last_updated": null}',
    ],
)
def test_malformed_file_starts_fresh(content):
    default_path().parent.mkdir()
    default_path().write_text(content)

    store = StatsStore()
    assert store.ports() == []
    store.record([Listener(80, 1, "nginx")])
    assert StatsStore().port(80) is not None


@pytest.mark.skipif(sys.platform == "win32", reason="no file ownership on Windows")
def test_history_written_as_root_belongs_to_the_home_owner(monkeypatch, home):
    owners = {}
    monkeypatch.setattr(stats.os, "geteuid", lambda: 0)
    monkeypatch.setattr(stats.os, "chown", lambda path, uid, gid: owners.update({path: uid}))

    StatsStore().record([Listener(80, 1, "nginx")])

    assert owners[default_path().parent] == home.stat().st_uid
    assert len(owners) == 2  # the directory and the file
