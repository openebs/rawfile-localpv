import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from utils import rawfile, snapshot_manager
from utils.snapshot_manager import SnapshotManager

VOLUME_ID = "pvc-source"
SNAPSHOT = "snap-1"
BLOCK = 4096
IMAGE_SIZE = 8 * 1024 * 1024


def stub_volume(monkeypatch, snap: Path):
    """Make restore_snapshot find a copy-on-write volume whose snapshot is `snap`."""
    monkeypatch.setattr(snapshot_manager, "metadata", lambda _: {"copy_on_write": True})
    monkeypatch.setattr(
        SnapshotManager,
        "_get_snapshot_path",
        lambda self, volume_id, name, temporary=False: snap,
    )


def test_restore_probes_destination_directory_and_reflinks(tmp_path, monkeypatch):
    snap = tmp_path / "source" / "snapshots" / f"{SNAPSHOT}.img"
    snap.parent.mkdir(parents=True)
    destination = tmp_path / "clone" / "disk.img"
    destination.parent.mkdir()
    stub_volume(monkeypatch, snap)
    snap.write_bytes(b"snapshot data")

    # Stand in for a reflink capable filesystem: cp --reflink=always works as long as
    # the target can be created, which it cannot when its parent is a file.
    commands = []

    def fake_run(cmd, *args, **kwargs):
        commands.append(cmd)
        *_, src, dst = cmd.split()
        if "--reflink=never" in cmd:
            shutil.copyfile(src, dst)
        else:
            if not Path(dst).parent.is_dir():
                raise subprocess.CalledProcessError(1, cmd, stderr=b"Not a directory")
            shutil.copyfile(src, dst)

    monkeypatch.setattr(rawfile, "run", fake_run)
    monkeypatch.setattr(snapshot_manager, "run", fake_run)

    SnapshotManager().restore_snapshot(VOLUME_ID, SNAPSHOT, destination)

    assert destination.read_bytes() == b"snapshot data"
    assert [c for c in commands if f"{snap} {destination}" in c] == [
        f"cp --sparse=auto --reflink=always {snap} {destination}"
    ]


def reflink_supported(directory: Path) -> bool:
    probe = directory / "probe"
    probe.write_bytes(b"x" * BLOCK)
    result = subprocess.run(
        ["cp", "--reflink=always", probe, directory / "probe-clone"],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


@pytest.fixture
def reflink_dir():
    # RAWFILE_TEST_REFLINK_DIR points at a Btrfs/XFS (reflink) mount; the default
    # temporary directory is usually tmpfs or ext4, which cannot share extents.
    with tempfile.TemporaryDirectory(
        dir=os.environ.get("RAWFILE_TEST_REFLINK_DIR")
    ) as d:
        path = Path(d)
        if not reflink_supported(path):
            pytest.skip("no reflink capable filesystem available")
        yield path


def extents(path: Path) -> list[str]:
    out = subprocess.run(
        ["filefrag", "-v", "-s", path], capture_output=True, text=True, check=True
    ).stdout
    # Extent rows look like: "   0:  0..  2047:  1234..  3281:  2048:   shared,eof"
    return [line for line in out.splitlines() if re.match(r"\s*\d+:\s", line)]


@pytest.mark.skipif(shutil.which("filefrag") is None, reason="filefrag not installed")
def test_restored_image_shares_extents_with_snapshot(reflink_dir, monkeypatch):
    snap = reflink_dir / "snapshots" / f"{SNAPSHOT}.img"
    snap.parent.mkdir()
    destination = reflink_dir / "clone" / "disk.img"
    destination.parent.mkdir()
    stub_volume(monkeypatch, snap)
    with open(snap, "wb") as f:
        f.write(os.urandom(IMAGE_SIZE))
        f.flush()
        os.fsync(f.fileno())

    SnapshotManager().restore_snapshot(VOLUME_ID, SNAPSHOT, destination)

    assert destination.read_bytes() == snap.read_bytes()
    rows = extents(destination)
    assert rows
    # A full copy gets private extents, a reflink clone shares every one of them
    assert all("shared" in row for row in rows), rows
