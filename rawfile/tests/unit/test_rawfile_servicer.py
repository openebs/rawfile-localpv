import json
from types import SimpleNamespace

import grpc
import pytest
import rawfile_servicer
from config import config
from csi import csi_pb2
from rawfile_servicer import NODE_NAME_TOPOLOGY_KEY, RawFileControllerServicer
from utils import storage_pool

VOLUME_ID = "pvc-1"
SIZE = 60


class Aborted(Exception):
    pass


class Context:
    # Like grpc's servicer context: abort() records the status and raises
    def __init__(self):
        self._state = SimpleNamespace(code=None, details=None)

    def abort(self, code, details):
        self._state.code = code
        self._state.details = details.encode()
        raise Aborted(details)


class TaskManager:
    def __init__(self, on_run=lambda: None):
        self.runs = []
        self._on_run = on_run

    def run_task(self, *args):
        self.runs.append(args)
        self._on_run()


@pytest.fixture
def meta_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config,
        "csi_driver",
        SimpleNamespace(
            metadata_dir=tmp_path,
            default_pool="default",
            storage_pools={"default": SimpleNamespace(path=tmp_path)},
            capabilities=SimpleNamespace(snapshots=SimpleNamespace(enabled=True)),
        ),
    )
    monkeypatch.setattr(rawfile_servicer, "send_event", lambda _: None)
    # Fast-forward the wait for the volume to be ready
    clock = iter(range(0, 3600, 10))
    monkeypatch.setattr(
        rawfile_servicer,
        "time",
        SimpleNamespace(time=lambda: next(clock), sleep=lambda _: None),
    )
    path = tmp_path / VOLUME_ID / "disk.meta"
    path.parent.mkdir()
    return path


@pytest.fixture
def capacity(monkeypatch):
    def set_capacity(value):
        monkeypatch.setattr(storage_pool, "get_capacity", lambda _: value)

    return set_capacity


def create_volume(task_manager):
    request = csi_pb2.CreateVolumeRequest(
        name=VOLUME_ID,
        capacity_range=csi_pb2.CapacityRange(required_bytes=SIZE),
        accessibility_requirements=csi_pb2.TopologyRequirement(
            preferred=[csi_pb2.Topology(segments={NODE_NAME_TOPOLOGY_KEY: "node-1"})]
        ),
    )
    context = Context()
    try:
        return RawFileControllerServicer(task_manager).CreateVolume(request, context)
    except Aborted:
        return context._state.code


def write_meta(meta_file, **meta):
    meta_file.write_text(json.dumps({"storage_pool": "default", **meta}))


def test_new_volume_starts_task(meta_file, capacity):
    capacity(SIZE)
    task_manager = TaskManager(on_run=lambda: write_meta(meta_file, ready=True))

    response = create_volume(task_manager)

    assert response.volume.volume_id == VOLUME_ID
    assert len(task_manager.runs) == 1


def test_new_volume_must_fit_in_pool(meta_file, capacity):
    capacity(SIZE - 1)
    task_manager = TaskManager()

    assert create_volume(task_manager) == grpc.StatusCode.RESOURCE_EXHAUSTED
    assert task_manager.runs == []


def test_retry_of_created_volume_ignores_capacity(meta_file, capacity):
    # The volume took the space it was asked for, the response got lost
    capacity(0)
    write_meta(meta_file, ready=True)
    task_manager = TaskManager()

    response = create_volume(task_manager)

    assert response.volume.volume_id == VOLUME_ID
    assert task_manager.runs == []


def test_retry_of_volume_being_created_ignores_capacity(meta_file, capacity):
    # e.g. restoring a snapshot takes longer than a CreateVolume call
    capacity(0)
    write_meta(meta_file, ready=False)
    task_manager = TaskManager()

    assert create_volume(task_manager) == grpc.StatusCode.DEADLINE_EXCEEDED


def test_retry_restarts_volume_left_not_ready(meta_file, capacity):
    # e.g. cloning an in-use volume until the task ran out of retries and was dropped
    capacity(SIZE)
    write_meta(meta_file, ready=False)
    task_manager = TaskManager(on_run=lambda: write_meta(meta_file, ready=True))

    response = create_volume(task_manager)

    assert response.volume.volume_id == VOLUME_ID
    assert len(task_manager.runs) == 1


def test_retry_does_not_bring_back_deleted_volume(meta_file, capacity):
    # Kept for its snapshots: the GC would remove a volume created over it
    capacity(SIZE)
    write_meta(meta_file, ready=False, deleted_at=1, gc_at=1)
    task_manager = TaskManager()

    assert create_volume(task_manager) == grpc.StatusCode.DEADLINE_EXCEEDED
    assert task_manager.runs == []
