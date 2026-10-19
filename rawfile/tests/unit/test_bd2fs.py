from types import SimpleNamespace

import pytest
from bd2fs import Bd2FsNodeServicer
from config import config
from csi import csi_pb2
from csi.csi_pb2 import NodeUnpublishVolumeRequest, NodeUnstageVolumeRequest
from rawfile_servicer import RawFileNodeServicer


@pytest.fixture
def meta_dir(tmp_path, monkeypatch):
    meta = tmp_path / "meta"
    meta.mkdir()
    monkeypatch.setattr(config, "csi_driver", SimpleNamespace(metadata_dir=meta))
    return meta


@pytest.fixture
def context():
    return SimpleNamespace(_state=SimpleNamespace(code=None, details=None))


def unpublish(volume_id, target, context):
    servicer = Bd2FsNodeServicer(bds=None, task_manager=None)
    request = NodeUnpublishVolumeRequest(
        volume_id=volume_id, target_path=target.as_posix()
    )
    return servicer.NodeUnpublishVolume(request, context)


def test_unpublish_unmounted_target_of_existing_volume(tmp_path, meta_dir, context):
    (meta_dir / "pvc-1").mkdir()
    target = tmp_path / "mount"
    target.mkdir()

    response = unpublish("pvc-1", target, context)

    assert isinstance(response, csi_pb2.NodeUnpublishVolumeResponse)
    assert not target.exists()


def test_unpublish_after_volume_was_deleted(tmp_path, meta_dir, context):
    # The volume's metadata dir (holding its lock file) is already gone
    target = tmp_path / "mount"
    target.mkdir()

    response = unpublish("pvc-deleted", target, context)

    assert isinstance(response, csi_pb2.NodeUnpublishVolumeResponse)
    assert not target.exists()
    assert not (meta_dir / "pvc-deleted").exists()


def test_unstage_after_volume_was_deleted(tmp_path, meta_dir, context):
    # What's left of a staged volume whose PV (and metadata) is already gone
    staging = tmp_path / "globalmount"
    (staging / "block").mkdir(parents=True)
    (staging / "block" / "dev").touch()

    servicer = Bd2FsNodeServicer(
        bds=RawFileNodeServicer(node_name="node-1"), task_manager=None
    )
    request = NodeUnstageVolumeRequest(
        volume_id="pvc-deleted", staging_target_path=staging.as_posix()
    )
    response = servicer.NodeUnstageVolume(request, context)

    assert isinstance(response, csi_pb2.NodeUnstageVolumeResponse)
    assert not (staging / "block").exists()
