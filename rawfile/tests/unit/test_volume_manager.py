import json
from types import SimpleNamespace

import pytest
from bd2fs import Bd2FsControllerServicer
from config import config
from csi import csi_pb2
from utils import rawfile
from utils import volume_manager as volume_manager_module
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
