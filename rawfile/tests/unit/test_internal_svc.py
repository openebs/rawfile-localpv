import json
from types import SimpleNamespace

import internal_svc
import pytest
from config import config
from internal import internal_pb2
from internal_svc import InternalServicer
from utils import rawfile
from utils import volume_manager as volume_manager_module

VOLUME_ID = "pvc-1"
SIZE = 60
OK = internal_pb2.ExpandRawFileStatus.OK
RESOURCE_EXHAUSTED = internal_pb2.ExpandRawFileStatus.RESOURCE_EXHAUSTED


@pytest.fixture
def volume(tmp_path, monkeypatch):
    """Creates a volume of SIZE bytes, with the given provisioning and physical size."""
    monkeypatch.setattr(
        config,
        "csi_driver",
        SimpleNamespace(
            metadata_dir=tmp_path / "meta",
            default_pool="default",
            storage_pools={"default": SimpleNamespace(path=tmp_path / "pool")},
        ),
    )
    monkeypatch.setattr(volume_manager_module, "attached_loops", lambda _: [])
    monkeypatch.setattr(rawfile, "update_permissions", lambda *_: None)

    def create(thin_provision, physical_size=SIZE, block_size=None):
        volume_dir = tmp_path / "pool" / VOLUME_ID
        volume_dir.mkdir(parents=True)
        (volume_dir / "disk.img").touch()
        meta = tmp_path / "meta" / VOLUME_ID
        meta.mkdir(parents=True)
        (meta / "disk.meta").write_text(
            json.dumps(
                {
                    "storage_pool": "default",
                    "img_file": (volume_dir / "disk.img").as_posix(),
                    "size": SIZE,
                    "thin_provision": thin_provision,
                    "block_size": block_size,
                }
            )
        )
        monkeypatch.setattr(
            internal_svc, "stat", lambda _: {"physical_size": physical_size}
        )
        return meta / "disk.meta"

    return create


@pytest.fixture
def grown_to(monkeypatch):
    """Records the size the image was grown to, by truncate or by fallocate."""
    grown = SimpleNamespace(truncate=None, fallocate=None)
    monkeypatch.setattr(
        internal_svc, "truncate", lambda _, size: setattr(grown, "truncate", size)
    )
    monkeypatch.setattr(
        internal_svc, "fallocate", lambda _, size: setattr(grown, "fallocate", size)
    )
    return grown


def expand(monkeypatch, new_size, capacity):
    monkeypatch.setattr(internal_svc, "get_capacity", lambda _: capacity)
    return InternalServicer(task_manager=None).ExpandRawFile(
        internal_pb2.ExpandRawFileRequest(volume_id=VOLUME_ID, new_size=new_size),
        context=None,
    )


def test_expand_thick_volume_larger_than_remaining_capacity(
    volume, grown_to, monkeypatch
):
    meta = volume(thin_provision=False)

    response = expand(monkeypatch, new_size=70, capacity=40)

    assert response.status == OK
    assert grown_to.fallocate == 70
    assert json.loads(meta.read_text())["size"] == 70


def test_expand_thin_volume_larger_than_remaining_capacity(
    volume, grown_to, monkeypatch
):
    meta = volume(thin_provision=True, physical_size=1)

    response = expand(monkeypatch, new_size=70, capacity=40)

    assert response.status == OK
    assert grown_to.truncate == 70
    assert json.loads(meta.read_text())["size"] == 70


@pytest.mark.parametrize("thin_provision", [False, True])
def test_expand_by_more_than_remaining_capacity(
    volume, grown_to, monkeypatch, thin_provision
):
    meta = volume(thin_provision=thin_provision)

    response = expand(monkeypatch, new_size=70, capacity=9)

    assert response.status == RESOURCE_EXHAUSTED
    assert grown_to.fallocate is None
    assert grown_to.truncate is None
    assert json.loads(meta.read_text())["size"] == SIZE


def test_expand_thick_volume_counts_holes_fallocate_would_allocate(
    volume, grown_to, monkeypatch
):
    # e.g. restored from a sparse snapshot or discarded by mkfs: fallocate allocates
    # the whole new size, 70 - 20 = 50 bytes more than what it holds on disk
    meta = volume(thin_provision=False, physical_size=20)

    response = expand(monkeypatch, new_size=70, capacity=49)

    assert response.status == RESOURCE_EXHAUSTED
    assert grown_to.fallocate is None
    assert json.loads(meta.read_text())["size"] == SIZE


@pytest.mark.parametrize("thin_provision", [False, True])
def test_expand_rounds_up_to_block_size(volume, grown_to, monkeypatch, thin_provision):
    # mkfs.xfs refuses a loop device which ends with a partial block
    meta = volume(thin_provision=thin_provision, block_size=4096)

    response = expand(monkeypatch, new_size=5000, capacity=8192)

    assert response.status == OK
    assert (grown_to.truncate if thin_provision else grown_to.fallocate) == 8192
    assert json.loads(meta.read_text())["size"] == 8192

    # A retry of the same expansion has nothing left to do
    grown_to.truncate = grown_to.fallocate = None

    response = expand(monkeypatch, new_size=5000, capacity=0)

    assert response.status == OK
    assert grown_to.truncate is None
    assert grown_to.fallocate is None
