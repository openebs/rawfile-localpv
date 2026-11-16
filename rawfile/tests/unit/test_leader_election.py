import threading
import time
from datetime import UTC, datetime, timedelta

import orchestrator.k8s as k8s_mod
import pytest
from lightkube import ApiError
from lightkube.models.coordination_v1 import LeaseSpec
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.coordination_v1 import Lease
from orchestrator.k8s import LeaderElection


class Resp:
    def __init__(self, code):
        self.status_code = code
        self.request = None

    def json(self):
        return {"code": self.status_code, "message": "fake"}


def api_error(code):
    return ApiError(response=Resp(code))


class FakeK8s:
    """Stores leases, enforcing the resourceVersion like the API server."""

    def __init__(self):
        self.lock = threading.Lock()
        self.objs = {}
        self.rv = 0

    def get(self, res, name, namespace=None):
        with self.lock:
            if name not in self.objs:
                raise api_error(404)
            return Lease.from_dict(self.objs[name])

    def _store(self, obj):
        self.rv += 1
        d = obj.to_dict()
        d["metadata"]["resourceVersion"] = str(self.rv)
        self.objs[obj.metadata.name] = d

    def create(self, obj):
        with self.lock:
            if obj.metadata.name in self.objs:
                raise api_error(409)
            self._store(obj)

    def replace(self, obj):
        with self.lock:
            cur = self.objs.get(obj.metadata.name)
            if cur is None:
                raise api_error(404)
            if cur["metadata"]["resourceVersion"] != obj.metadata.resourceVersion:
                raise api_error(409)
            self._store(obj)

    def spec(self, name) -> LeaseSpec:
        return Lease.from_dict(self.objs[name]).spec


@pytest.fixture
def fake(monkeypatch):
    fake = FakeK8s()
    monkeypatch.setattr(k8s_mod, "k8s", lambda: fake)
    return fake


@pytest.fixture
def elections(fake):
    started = []

    def make(n, lease_duration=2, retry_period=0.1):
        es = [
            LeaderElection("test", f"node-{i}", lease_duration, retry_period)
            for i in range(n)
        ]
        for e in es:
            e.start()
        started.extend(es)
        return es

    yield make
    # the election threads can't be stopped, keep them away from the api
    for e in started:
        e._try_acquire_or_renew = lambda: False


def leaders(es):
    return [e.identity for e in es if e.leader.is_set()]


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def store_lease(fake, holder, renewed, duration=2):
    fake.create(
        Lease(
            metadata=ObjectMeta(name="test", namespace="x"),
            spec=LeaseSpec(
                holderIdentity=holder,
                acquireTime=renewed,
                renewTime=renewed,
                leaseDurationSeconds=duration,
                leaseTransitions=3,
            ),
        )
    )


def test_unexpired_lease_is_not_taken(fake):
    store_lease(fake, "other", datetime.now(UTC))
    assert not LeaderElection("test", "me", lease_duration=2)._try_acquire_or_renew()
    assert fake.spec("test").holderIdentity == "other"


def test_expired_lease_is_taken_over(fake):
    store_lease(fake, "other", datetime.now(UTC) - timedelta(seconds=3))
    assert LeaderElection("test", "me", lease_duration=2)._try_acquire_or_renew()
    spec = fake.spec("test")
    assert spec.holderIdentity == "me"
    assert spec.leaseTransitions == 4


def test_renew_keeps_acquire_time(fake):
    e = LeaderElection("test", "me", lease_duration=2)
    assert e._try_acquire_or_renew()
    acquired = fake.spec("test").acquireTime
    assert e._try_acquire_or_renew()
    spec = fake.spec("test")
    assert spec.acquireTime == acquired
    assert spec.renewTime > acquired
    assert spec.leaseTransitions == 0


def test_concurrent_acquire_conflicts(fake):
    """Both read the free lease, only the first write wins."""
    a, b = (LeaderElection("test", n, lease_duration=2) for n in "ab")
    get = fake.get
    read = threading.Barrier(2)

    def racy_get(*args, **kwargs):
        lease = get(*args, **kwargs) if fake.objs else None
        read.wait(timeout=5)
        if lease is None:
            raise api_error(404)
        return lease

    fake.get = racy_get
    results = {}

    def run(e):
        try:
            results[e.identity] = e._try_acquire_or_renew()
        except ApiError as err:
            results[e.identity] = err.status.code

    threads = [threading.Thread(target=run, args=(e,)) for e in (a, b)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert set(results.values()) == {True, 409}, results
    winner = next(n for n, r in results.items() if r is True)
    assert fake.spec("test").holderIdentity == winner


def test_single_leader(elections):
    es = elections(5)
    assert wait_for(lambda: len(leaders(es)) == 1)
    first = leaders(es)
    # stays stable over several renewals
    for _ in range(10):
        time.sleep(0.05)
        assert leaders(es) == first


def test_failing_leader_steps_down_before_takeover(elections, fake):
    es = elections(3)
    assert wait_for(lambda: len(leaders(es)) == 1)
    (first,) = leaders(es)
    dead = next(e for e in es if e.identity == first)

    def boom():
        raise RuntimeError("simulated failure")

    failed = time.monotonic()
    dead._try_acquire_or_renew = boom
    # drops the leadership straight away...
    assert wait_for(lambda: leaders(es) == [], timeout=1)
    # ...while the others wait for the lease to expire
    assert wait_for(lambda: len(leaders(es)) == 1)
    assert time.monotonic() - failed >= dead.lease_duration - dead.retry_period * 2
    (second,) = leaders(es)
    assert second != first
    spec = fake.spec("test")
    assert spec.holderIdentity == second
    assert spec.leaseTransitions == 1


def test_is_leader_false_when_renewal_is_stale():
    """A paused process still has `leader` set, but may have lost the lease."""
    e = LeaderElection("test", "me", lease_duration=3, retry_period=1)
    assert not e.is_leader()
    e.leader.set()
    e._renewed = time.monotonic()
    assert e.is_leader()
    e._renewed = time.monotonic() - 2.1
    assert not e.is_leader()
