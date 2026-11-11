from types import SimpleNamespace

import bd2fs
import grpc
import pytest
from bd2fs import Bd2FsControllerServicer, Bd2FsNodeServicer
from config import config
from csi import csi_pb2
from csi.csi_pb2 import (
    CreateVolumeRequest,
    NodePublishVolumeRequest,
    NodeUnpublishVolumeRequest,
    NodeUnstageVolumeRequest,
    VolumeCapability,
)

AccessMode = VolumeCapability.AccessMode.Mode


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


def ready_volume(meta_dir, volume_id):
    (meta_dir / volume_id).mkdir()
    (meta_dir / volume_id / "disk.meta").write_text('{"ready": true}')


@pytest.fixture
def mounts(monkeypatch):
    # Records the publish mounts, and lists them as the mountpoints of the volume
    mounted = []

    def mount(device, mountpoint, readonly=False, options=None):
        mounted.append(mountpoint)

    monkeypatch.setattr(bd2fs, "mount", mount)
    monkeypatch.setattr(bd2fs, "get_mountpoints_for_device", lambda dev: mounted)
    return mounted


def publish(volume_id, staging, target, mode, context):
    servicer = Bd2FsNodeServicer(bds=None, task_manager=None)
    request = NodePublishVolumeRequest(
        volume_id=volume_id,
        staging_target_path=staging.as_posix(),
        target_path=target.as_posix(),
        volume_capability=VolumeCapability(
            mount=VolumeCapability.MountVolume(),
            access_mode=VolumeCapability.AccessMode(mode=mode),
        ),
    )
    return servicer.NodePublishVolume(request, context)


def test_publish_single_writer_volume_once(tmp_path, meta_dir, context, mounts):
    ready_volume(meta_dir, "pvc-1")
    staging = tmp_path / "globalmount"
    # The filesystem's staging mount isn't a publication
    mounts.append((staging / "mount").as_posix())
    target = tmp_path / "pod-1"

    response = publish(
        "pvc-1", staging, target, AccessMode.SINGLE_NODE_SINGLE_WRITER, context
    )

    assert isinstance(response, csi_pb2.NodePublishVolumeResponse)
    assert mounts == [(staging / "mount").as_posix(), target.as_posix()]


def test_publish_single_writer_volume_again_at_same_target(
    tmp_path, meta_dir, context, mounts
):
    ready_volume(meta_dir, "pvc-1")
    staging = tmp_path / "globalmount"
    target = tmp_path / "pod-1"
    publish("pvc-1", staging, target, AccessMode.SINGLE_NODE_SINGLE_WRITER, context)

    response = publish(
        "pvc-1", staging, target, AccessMode.SINGLE_NODE_SINGLE_WRITER, context
    )

    assert isinstance(response, csi_pb2.NodePublishVolumeResponse)


def test_publish_single_writer_volume_published_elsewhere(
    tmp_path, meta_dir, context, mounts
):
    ready_volume(meta_dir, "pvc-1")
    staging = tmp_path / "globalmount"
    first, second = tmp_path / "pod-1", tmp_path / "pod-2"
    publish("pvc-1", staging, first, AccessMode.SINGLE_NODE_SINGLE_WRITER, context)

    with pytest.raises(Aborted):
        publish("pvc-1", staging, second, AccessMode.SINGLE_NODE_SINGLE_WRITER, context)

    assert context._state.code == grpc.StatusCode.FAILED_PRECONDITION
    assert first.as_posix() in context._state.details.decode()
    assert mounts == [first.as_posix()]


@pytest.mark.parametrize(
    "mode",
    [AccessMode.SINGLE_NODE_MULTI_WRITER, AccessMode.SINGLE_NODE_WRITER],
    ids=AccessMode.Name,
)
def test_publish_multi_writer_volume_at_several_targets(
    tmp_path, meta_dir, context, mounts, mode
):
    ready_volume(meta_dir, "pvc-1")
    staging = tmp_path / "globalmount"
    first, second = tmp_path / "pod-1", tmp_path / "pod-2"
    publish("pvc-1", staging, first, mode, context)

    response = publish("pvc-1", staging, second, mode, context)

    assert isinstance(response, csi_pb2.NodePublishVolumeResponse)
    assert mounts == [first.as_posix(), second.as_posix()]


class Bds:
    def CreateVolume(self, request, context):
        return csi_pb2.CreateVolumeResponse()


def create_volume(mode, context):
    servicer = Bd2FsControllerServicer(bds=Bds(), task_manager=None)
    request = CreateVolumeRequest(
        name="pvc-1",
        volume_capabilities=[
            VolumeCapability(
                mount=VolumeCapability.MountVolume(),
                access_mode=VolumeCapability.AccessMode(mode=mode),
            )
        ],
    )
    return servicer.CreateVolume(request, context)


@pytest.mark.parametrize(
    "mode",
    [
        AccessMode.SINGLE_NODE_WRITER,
        AccessMode.SINGLE_NODE_SINGLE_WRITER,
        AccessMode.SINGLE_NODE_MULTI_WRITER,
    ],
    ids=AccessMode.Name,
)
def test_create_volume_single_node_access_modes(context, mode):
    response = create_volume(mode, context)

    assert isinstance(response, csi_pb2.CreateVolumeResponse)


@pytest.mark.parametrize(
    "mode",
    [
        AccessMode.SINGLE_NODE_READER_ONLY,
        AccessMode.MULTI_NODE_READER_ONLY,
        AccessMode.MULTI_NODE_SINGLE_WRITER,
        AccessMode.MULTI_NODE_MULTI_WRITER,
    ],
    ids=AccessMode.Name,
)
def test_create_volume_unsupported_access_modes(context, mode):
    with pytest.raises(Aborted):
        create_volume(mode, context)

    assert context._state.code == grpc.StatusCode.INVALID_ARGUMENT
