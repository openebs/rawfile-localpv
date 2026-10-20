from types import SimpleNamespace

import bd2fs
import grpc
import pytest
from bd2fs import Bd2FsNodeServicer
from config import config
from csi import csi_pb2
from csi.csi_pb2 import NodeUnpublishVolumeRequest, NodeUnstageVolumeRequest


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
