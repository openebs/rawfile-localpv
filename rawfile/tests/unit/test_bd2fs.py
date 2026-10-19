from types import SimpleNamespace

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


def test_unpublish_after_volume_was_deleted(tmp_path, meta_dir, context):
    target = tmp_path / "mount"
    target.mkdir()

    with pytest.raises(Aborted):
        unpublish("pvc-deleted", target, context)

    assert context._state.code == grpc.StatusCode.NOT_FOUND
    # Nothing is touched for a volume that no longer exists
    assert target.is_dir()
    assert not (meta_dir / "pvc-deleted").exists()


def test_unstage_after_volume_was_deleted(tmp_path, meta_dir, context):
    staging = tmp_path / "globalmount"
    (staging / "block").mkdir(parents=True)
    (staging / "block" / "dev").touch()

    servicer = Bd2FsNodeServicer(bds=None, task_manager=None)
    request = NodeUnstageVolumeRequest(
        volume_id="pvc-deleted", staging_target_path=staging.as_posix()
    )
    with pytest.raises(Aborted):
        servicer.NodeUnstageVolume(request, context)

    assert context._state.code == grpc.StatusCode.NOT_FOUND
    assert (staging / "block" / "dev").exists()
