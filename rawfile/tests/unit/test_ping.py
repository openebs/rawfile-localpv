import threading
import time
from datetime import timedelta

import analytics.ga4.ping as ping_mod
import pytest


class FakeConfigMap:
    def __init__(self):
        self.lock = threading.Lock()
        self.data = {}

    def read(self, name):
        with self.lock:
            return dict(self.data)

    def write(self, name, key, value, overwrite=False):
        with self.lock:
            if overwrite or key not in self.data:
                self.data[key] = value


class FakeUsage:
    def __init__(self, who, sent):
        self.who = who
        self.sent = sent

    def refresh(self):
        pass

    def send_install(self):
        self.sent.append((self.who, "install", time.monotonic()))

    def send_ping(self):
        self.sent.append((self.who, "ping", time.monotonic()))


class FakeElection:
    retry_period = 0.05

    def __init__(self):
        self.leader = threading.Event()
        # a paused process: `leader` still set, but the lease may be gone
        self.stale = False

    def is_leader(self):
        return self.leader.is_set() and not self.stale


@pytest.fixture
def cm(monkeypatch):
    cm = FakeConfigMap()
    monkeypatch.setattr(ping_mod, "read_config_map", cm.read)
    monkeypatch.setattr(ping_mod, "write_config_map", cm.write)
    return cm


@pytest.fixture
def sent():
    return []


@pytest.fixture
def pinger(cm, sent):
    elections = []

    def start(who, ping_delta):
        election = FakeElection()
        p = ping_mod.Ping(lambda: FakeUsage(who, sent), ping_delta, election)
        threading.Thread(target=p.run, daemon=True).start()
        elections.append(election)
        return election

    yield start
    # the ping threads can't be stopped, park them waiting for the leadership
    for e in elections:
        e.leader.clear()


def pings(sent, who=None):
    return [ts for w, ev, ts in sent if ev == "ping" and who in (None, w)]


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_only_leader_pings(pinger, sent):
    a = pinger("a", timedelta(seconds=0.3))
    pinger("b", timedelta(seconds=0.3))
    a.leader.set()
    assert wait_for(lambda: len(pings(sent)) >= 2)
    assert sent[0][:2] == ("a", "install")
    assert pings(sent, "b") == []


def test_stale_leader_does_not_ping(pinger, sent):
    """A paused leader resumes thinking it still leads, while another node
    took over the lease: only the new leader pings."""
    delta = timedelta(seconds=0.3)
    a = pinger("a", delta)
    b = pinger("b", delta)
    a.leader.set()
    assert wait_for(lambda: len(pings(sent, "a")) >= 2)

    a.stale = True
    b.leader.set()
    paused = len(pings(sent, "a"))
    assert wait_for(lambda: len(pings(sent, "b")) >= 3)
    # at most one ping in flight when a got paused
    assert len(pings(sent, "a")) - paused <= 1
    # b carries on the schedule, without a new install
    assert [w for w, ev, _ in sent if ev == "install"] == ["a"]

    # a's election notices it lost the lease, b keeps going
    a.leader.clear()
    a.stale = False
    n_a = len(pings(sent, "a"))
    n_b = len(pings(sent, "b"))
    assert wait_for(lambda: len(pings(sent, "b")) >= n_b + 2)
    assert len(pings(sent, "a")) == n_a


def test_skips_ping_if_another_leader_pinged(pinger, sent, cm):
    """While waiting for the ping, another leader pinged (eg: we were paused
    and regained the lease): reschedule from its ping instead."""
    a = pinger("a", timedelta(seconds=1))
    a.leader.set()
    assert wait_for(lambda: len(sent) == 1)
    start = sent[0][2]

    time.sleep(0.5)
    other = time.monotonic()
    cm.write("x", "last-ping-ts", ping_mod.now_to_str(), overwrite=True)

    # our ping was due at +1s but must be skipped, the next is due at +1.5s
    assert wait_for(lambda: pings(sent), timeout=3)
    assert pings(sent)[0] - start >= 1.4
    assert pings(sent)[0] - other >= 0.9


def test_regained_leader_reloads_ping_ts(pinger, sent, cm):
    """After losing the lease, a returning leader resumes from the last ping
    recorded by the other leader, rather than its own stale schedule."""
    delta = timedelta(seconds=0.5)
    a = pinger("a", delta)
    b = pinger("b", delta)
    a.leader.set()
    assert wait_for(lambda: "last-ping-ts" in cm.read("x"))

    a.leader.clear()
    b.leader.set()
    a_ts = cm.read("x").get("last-ping-ts")
    assert wait_for(lambda: cm.read("x").get("last-ping-ts") != a_ts)
    b_pinged = pings(sent, "b")[0]
    n_a = len(pings(sent, "a"))

    b.leader.clear()
    a.leader.set()
    assert wait_for(lambda: len(pings(sent, "a")) > n_a)
    assert pings(sent, "a")[n_a] - b_pinged >= 0.45
