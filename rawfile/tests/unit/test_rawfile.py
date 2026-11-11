import json
from types import SimpleNamespace

import pytest
import rawfile_servicer
from config import config
from csi import csi_pb2
from rawfile_servicer import RawFileNodeServicer
from utils import rawfile
from utils.rawfile import attach_loop, round_up_to_block_size

VOLUME_ID = "pvc-1"
LOOP_DEV = "/dev/loop0"


@pytest.mark.parametrize(
    "size,block_size,rounded",
    [
        (5000, None, 5000),
        (4096, 4096, 4096),
        (4097, 4096, 8192),
        (10**9, 4096, 1_000_001_536),
        (10**9 + 1, 512, 1_000_000_512),
    ],
)
def test_round_up_to_block_size(size, block_size, rounded):
    assert round_up_to_block_size(size, block_size) == rounded


@pytest.fixture
def losetup(monkeypatch):
    """Stands in for losetup, records the commands run to attach a loop device."""
    commands = []
    attached = []

    def fake_run(cmd, *args, **kwargs):
        commands.append(cmd)
        out = b""
        if cmd == "losetup -f":
            out = f"{LOOP_DEV}\n".encode()
        elif cmd.startswith("losetup -j"):
            out = "".join(f"{LOOP_DEV}: []: ({file})\n" for file in attached).encode()
        elif cmd.startswith("losetup --direct-io=on"):
            attached.append(cmd.rsplit(" ", 1)[-1])
        return SimpleNamespace(stdout=out)

    monkeypatch.setattr(rawfile, "run", fake_run)
    return SimpleNamespace(
        attaches=lambda: [c for c in commands if c.startswith("losetup --direct")],
    )


@pytest.mark.parametrize(
    "block_size,command",
    [
        (None, "losetup --direct-io=on -f {file}"),
        (512, "losetup --direct-io=on --sector-size 512 -f {file}"),
        (4096, "losetup --direct-io=on --sector-size 4096 -f {file}"),
    ],
)
def test_attach_loop_block_size(tmp_path, losetup, block_size, command):
    file = tmp_path / "disk.img"

    assert attach_loop(file, block_size=block_size) == LOOP_DEV

    assert losetup.attaches() == [command.format(file=file)]


def test_attach_loop_already_attached(tmp_path, losetup):
    file = tmp_path / "disk.img"
    attach_loop(file, block_size=4096)

    assert attach_loop(file, block_size=4096) == LOOP_DEV

    assert len(losetup.attaches()) == 1


@pytest.mark.parametrize("block_size", [None, 4096])
def test_stage_attaches_with_volume_block_size(tmp_path, monkeypatch, block_size):
    monkeypatch.setattr(config, "csi_driver", SimpleNamespace(metadata_dir=tmp_path))
    img_file = tmp_path / "disk.img"
    meta = {"img_file": img_file.as_posix(), "ready": True}
    # Volumes created before the block size was configurable have none in their metadata
    if block_size:
        meta["block_size"] = block_size
    (tmp_path / VOLUME_ID).mkdir()
    (tmp_path / VOLUME_ID / "disk.meta").write_text(json.dumps(meta))
    attached = []

    def fake_attach_loop(file, block_size=None):
        attached.append((file, block_size))
        return LOOP_DEV

    monkeypatch.setattr(rawfile_servicer, "attach_loop", fake_attach_loop)
    staging = tmp_path / "block"
    staging.mkdir()

    RawFileNodeServicer("node-1").NodeStageVolume(
        csi_pb2.NodeStageVolumeRequest(
            volume_id=VOLUME_ID, staging_target_path=staging.as_posix()
        ),
        None,
    )

    assert attached == [(img_file, block_size)]
    assert (staging / "dev").readlink().as_posix() == LOOP_DEV
