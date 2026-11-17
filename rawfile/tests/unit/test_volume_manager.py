import json
import shutil
from types import SimpleNamespace

import pytest
from bd2fs import Bd2FsControllerServicer
from config import config
from csi import csi_pb2
from utils import rawfile
from utils import volume_manager as volume_manager_module
from utils.snapshot_manager import manager as snapshot_manager
from utils.volume_manager import VolumeSource
from utils.volume_manager import manager as volume_manager

VOLUME_ID = "pvc-1"
SNAPSHOT = "snap-1"


@pytest.fixture
def volume(tmp_path, monkeypatch):
    """A volume with one snapshot, laid out as create_volume/create_snapshot do."""
    meta = tmp_path / "meta"
    pool = tmp_path / "pool"
    monkeypatch.setattr(
        config,
        "csi_driver",
        SimpleNamespace(
            metadata_dir=meta,
            default_pool="default",
            storage_pools={"default": SimpleNamespace(path=pool)},
            capabilities=SimpleNamespace(snapshots=SimpleNamespace(enabled=True)),
        ),
    )
    monkeypatch.setattr(volume_manager_module, "attached_loops", lambda _: [])
    # The driver runs as root: the 0600 directories it leaves behind are not
    # traversable by an unprivileged test user
    monkeypatch.setattr(rawfile, "update_permissions", lambda *_: None)

    volume_dir = pool / VOLUME_ID
    (volume_dir / "snapshots" / "temp").mkdir(parents=True)
    (volume_dir / "disk.img").write_bytes(b"data")
    (volume_dir / "snapshots" / f"{SNAPSHOT}.img").write_bytes(b"data")
    (meta / VOLUME_ID).mkdir(parents=True)
    (meta / VOLUME_ID / "disk.meta").write_text(
        json.dumps(
            {
                "volume_id": VOLUME_ID,
                "storage_pool": "default",
                "img_file": (volume_dir / "disk.img").as_posix(),
                "size": 4,
                "ready": True,
            }
        )
    )
    return SimpleNamespace(dir=volume_dir, meta=meta / VOLUME_ID)


def test_delete_volume_with_snapshot_keeps_snapshot(volume):
    volume_manager.delete_volume(VOLUME_ID)

    assert not (volume.dir / "disk.img").exists()
    assert (volume.dir / "snapshots" / f"{SNAPSHOT}.img").exists()
    assert (volume.meta / "disk.meta").exists()


def test_delete_last_snapshot_removes_deleted_volume(volume):
    volume_manager.delete_volume(VOLUME_ID)

    servicer = Bd2FsControllerServicer(bds=None, task_manager=None)
    context = SimpleNamespace(_state=SimpleNamespace(code=None, details=None))
    response = servicer.DeleteSnapshot(
        csi_pb2.DeleteSnapshotRequest(snapshot_id=f"{VOLUME_ID}/{SNAPSHOT}"), context
    )

    assert isinstance(response, csi_pb2.DeleteSnapshotResponse)
    assert not volume.dir.exists()
    assert not volume.meta.exists()


def test_gc_removes_deleted_volume_once_snapshots_are_gone(volume):
    volume_manager.delete_volume(VOLUME_ID)
    (volume.dir / "snapshots" / f"{SNAPSHOT}.img").unlink()

    assert volume_manager.gc_all_volumes(dry_run=False) == [True]
    assert not volume.dir.exists()
    assert not volume.meta.exists()


@pytest.fixture
def pools(tmp_path, monkeypatch):
    """A pool leaving the loop devices' block size to losetup, and one using 4096."""
    monkeypatch.setattr(
        config,
        "csi_driver",
        SimpleNamespace(
            metadata_dir=tmp_path / "meta",
            default_pool="default",
            storage_pools={
                "default": SimpleNamespace(path=tmp_path / "default", block_size=None),
                "zfs": SimpleNamespace(path=tmp_path / "zfs", block_size=4096),
            },
        ),
    )
    for pool in config.csi_driver.storage_pools.values():
        pool.path.mkdir()
    monkeypatch.setattr(rawfile, "update_permissions", lambda *_: None)

    # Snapshots and restores copy the image, as cp does without CoW
    def create_snapshot(volume_id, name, temporary=False, **_):
        path = snapshot_manager._get_snapshot_path(volume_id, name, temporary)
        shutil.copyfile(rawfile.img_file(volume_id), path)

    def restore_snapshot(volume_id, name, destination, temporary=False):
        path = snapshot_manager._get_snapshot_path(volume_id, name, temporary)
        shutil.copyfile(path, destination)

    monkeypatch.setattr(snapshot_manager, "create_snapshot", create_snapshot)
    monkeypatch.setattr(snapshot_manager, "restore_snapshot", restore_snapshot)


def create_volume(volume_id, storage_pool, size=4096, **kwargs):
    volume_manager.create_volume(
        volume_id, size, storage_pool, thin_provision=True, **kwargs
    )
    return rawfile.metadata(volume_id)


@pytest.mark.parametrize("storage_pool,block_size", [("default", None), ("zfs", 4096)])
def test_create_volume_records_pool_block_size(pools, storage_pool, block_size):
    meta = create_volume("pvc-new", storage_pool)

    assert meta["ready"]
    assert meta["block_size"] == block_size


@pytest.mark.parametrize("storage_pool,image_size", [("default", 5000), ("zfs", 8192)])
def test_create_volume_rounds_up_to_block_size(pools, storage_pool, image_size):
    # mkfs.xfs refuses a loop device which ends with a partial block
    meta = create_volume("pvc-new", storage_pool, size=5000)

    assert meta["size"] == image_size
    assert rawfile.img_file("pvc-new").stat().st_size == image_size


@pytest.mark.parametrize(
    "source_pool,storage_pool,block_size",
    [("zfs", "default", 4096), ("default", "zfs", None)],
)
@pytest.mark.parametrize("source_type", [VolumeSource.snapshot, VolumeSource.volume])
def test_cloned_volume_keeps_source_block_size(
    pools, source_pool, storage_pool, block_size, source_type
):
    # The source's filesystem was created for the source's block size, whatever
    # the block size of the pool the clone is created in is
    create_volume("pvc-source", source_pool)
    source_id = "pvc-source"
    if source_type == VolumeSource.snapshot:
        snapshot_manager.create_snapshot("pvc-source", SNAPSHOT)
        source_id = f"pvc-source/{SNAPSHOT}"

    meta = create_volume(
        "pvc-clone", storage_pool, source_type=source_type, source_id=source_id
    )

    assert meta["ready"]
    assert meta["block_size"] == block_size
