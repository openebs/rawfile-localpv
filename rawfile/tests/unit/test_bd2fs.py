from types import SimpleNamespace

import bd2fs
import grpc
import pytest
from bd2fs import Bd2FsControllerServicer, Bd2FsNodeServicer
from config import config
from csi import csi_pb2
from csi.csi_pb2 import (
    ListSnapshotsRequest,
    NodeUnpublishVolumeRequest,
    NodeUnstageVolumeRequest,
)


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


@pytest.fixture
def meta_dir(tmp_path, monkeypatch):
    meta = tmp_path / "meta"
    meta.mkdir()
    monkeypatch.setattr(config, "csi_driver", SimpleNamespace(metadata_dir=meta))
    return meta


@pytest.fixture
def context():
    return Context()


def unpublish(volume_id, target, context):
    servicer = Bd2FsNodeServicer(bds=None, task_manager=None)
    request = NodeUnpublishVolumeRequest(
        volume_id=volume_id, target_path=target.as_posix()
    )
    return servicer.NodeUnpublishVolume(request, context)


def test_unpublish_unmounted_target_of_existing_volume(tmp_path, meta_dir, context):
    (meta_dir / "pvc-1").mkdir()
    (meta_dir / "pvc-1" / "disk.meta").write_text("{}")
    target = tmp_path / "mount"
    target.mkdir()

    response = unpublish("pvc-1", target, context)

    assert isinstance(response, csi_pb2.NodeUnpublishVolumeResponse)
    assert not target.exists()


def still_mounted(*mountpoints):
    def get_device(mountpoint):
        return "/dev/loop0" if mountpoint in mountpoints else None

    return get_device


def test_unpublish_after_volume_was_deleted(tmp_path, meta_dir, context):
    # The volume's metadata (and lock file) is already gone, its target unmounted
    target = tmp_path / "mount"
    target.mkdir()

    response = unpublish("pvc-deleted", target, context)

    assert isinstance(response, csi_pb2.NodeUnpublishVolumeResponse)
    assert not target.exists()
    assert not (meta_dir / "pvc-deleted").exists()


def test_unpublish_deleted_volume_still_mounted(
    tmp_path, meta_dir, context, monkeypatch
):
    target = tmp_path / "mount"
    target.mkdir()
    monkeypatch.setattr(
        bd2fs, "get_device_for_mountpoint", still_mounted(target.as_posix())
    )

    with pytest.raises(Aborted):
        unpublish("pvc-deleted", target, context)

    assert context._state.code == grpc.StatusCode.NOT_FOUND
    assert target.is_dir()


def unstage(volume_id, staging, context):
    servicer = Bd2FsNodeServicer(bds=None, task_manager=None)
    request = NodeUnstageVolumeRequest(
        volume_id=volume_id, staging_target_path=staging.as_posix()
    )
    return servicer.NodeUnstageVolume(request, context)


def deleted_volume_staging(tmp_path):
    # What's left of a staged volume whose PV (and metadata) is already gone
    staging = tmp_path / "globalmount"
    (staging / "mount").mkdir(parents=True)
    (staging / "device").touch()
    (staging / "block").mkdir()
    (staging / "block" / "dev").symlink_to("/dev/loop0")
    return staging


def test_unstage_after_volume_was_deleted(tmp_path, meta_dir, context):
    staging = deleted_volume_staging(tmp_path)

    response = unstage("pvc-deleted", staging, context)

    assert isinstance(response, csi_pb2.NodeUnstageVolumeResponse)
    assert list(staging.iterdir()) == []


def test_unstage_deleted_volume_still_mounted(tmp_path, meta_dir, context, monkeypatch):
    staging = deleted_volume_staging(tmp_path)
    monkeypatch.setattr(
        bd2fs,
        "get_device_for_mountpoint",
        still_mounted((staging / "mount").as_posix()),
    )

    with pytest.raises(Aborted):
        unstage("pvc-deleted", staging, context)

    assert context._state.code == grpc.StatusCode.NOT_FOUND
    assert sorted(p.name for p in staging.iterdir()) == ["block", "device", "mount"]


VOLUME_SNAPSHOTS = {"pvc-1": ["snap-a", "snap-b"], "pvc-2": ["snap-c"]}


@pytest.fixture
def snapshots(tmp_path, monkeypatch):
    meta = tmp_path / "meta"
    pool = tmp_path / "pool"
    for volume_id, names in VOLUME_SNAPSHOTS.items():
        (meta / volume_id).mkdir(parents=True)
        (meta / volume_id / "disk.meta").write_text('{"storage_pool": "default"}')
        (pool / volume_id / "snapshots").mkdir(parents=True)
        for name in names:
            (pool / volume_id / "snapshots" / f"{name}.img").write_bytes(b"data")
    monkeypatch.setattr(
        config,
        "csi_driver",
        SimpleNamespace(
            metadata_dir=meta,
            storage_pools={"default": SimpleNamespace(path=pool)},
            capabilities=SimpleNamespace(snapshots=SimpleNamespace(enabled=True)),
        ),
    )
    return [f"{v}/{name}" for v, names in VOLUME_SNAPSHOTS.items() for name in names]


def list_snapshots(context, **kwargs):
    servicer = Bd2FsControllerServicer(bds=None, task_manager=None)
    return servicer.ListSnapshots(ListSnapshotsRequest(**kwargs), context)


def snapshot_ids(response):
    return [entry.snapshot.snapshot_id for entry in response.entries]


def test_list_snapshots_without_max_entries_returns_all(snapshots, context):
    response = list_snapshots(context)

    assert snapshot_ids(response) == snapshots
    assert response.next_token == ""


def test_list_snapshots_paginates_with_max_entries(snapshots, context):
    first = list_snapshots(context, max_entries=2)

    assert snapshot_ids(first) == snapshots[:2]
    assert first.next_token

    second = list_snapshots(context, max_entries=2, starting_token=first.next_token)

    assert snapshot_ids(second) == snapshots[2:]
    assert second.next_token == ""


def test_list_snapshots_by_source_volume_id(snapshots, context):
    response = list_snapshots(context, source_volume_id="pvc-2")

    assert snapshot_ids(response) == ["pvc-2/snap-c"]
    assert response.next_token == ""


def test_list_snapshots_by_snapshot_id(snapshots, context):
    response = list_snapshots(context, snapshot_id="pvc-1/snap-b")

    assert snapshot_ids(response) == ["pvc-1/snap-b"]
    assert response.next_token == ""


@pytest.mark.parametrize(
    "request_args",
    [
        {"snapshot_id": "pvc-1/snap-missing"},
        {"snapshot_id": "pvc-deleted/snap-a"},
        {"snapshot_id": "not-a-snapshot-id"},
        {"snapshot_id": "pvc-1/"},
        {"snapshot_id": "pvc-1/snap-a", "source_volume_id": "pvc-2"},
        {"source_volume_id": "pvc-deleted"},
    ],
)
def test_list_snapshots_returns_empty_list_for_unknown_snapshot(
    snapshots, context, request_args
):
    response = list_snapshots(context, **request_args)

    assert snapshot_ids(response) == []
    assert response.next_token == ""
