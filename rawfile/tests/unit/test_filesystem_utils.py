import filesystem.utils
import pytest
from filesystem.utils import get_mountpoints_for_device


@pytest.fixture
def device(tmp_path):
    # Stands in for /dev/loop1, only its path is looked at for filesystem mounts
    dev = tmp_path / "dev" / "loop1"
    dev.parent.mkdir()
    dev.touch()
    return dev


@pytest.fixture
def mountinfo(tmp_path, monkeypatch):
    path = tmp_path / "mountinfo"
    monkeypatch.setattr(filesystem.utils, "MOUNTINFO", path.as_posix())

    def write(*lines):
        path.write_text("".join(f"{line}\n" for line in lines))

    return write


def test_filesystem_mounts_of_device(device, mountinfo):
    mountinfo(
        "21 1 8:1 / / rw,relatime shared:1 - ext4 /dev/sda1 rw",
        f"30 21 7:1 / /kubelet/globalmount/mount rw,relatime shared:2 - ext4 {device} rw",
        f"31 21 7:1 / /kubelet/pods/1/mount rw,relatime shared:2 - ext4 {device} rw",
        "32 21 7:2 / /kubelet/pods/2/mount rw,relatime shared:3 - ext4 /dev/loop2 rw",
    )

    assert get_mountpoints_for_device(device.as_posix()) == [
        "/kubelet/globalmount/mount",
        "/kubelet/pods/1/mount",
    ]


def test_mountpoints_without_optional_fields_and_escaped(device, mountinfo):
    mountinfo(
        f"30 21 0:40 / /kubelet/pod\\0401/mount rw - btrfs {device} rw,space_cache=v2",
    )

    assert get_mountpoints_for_device(device.as_posix()) == ["/kubelet/pod 1/mount"]


def test_bind_mounts_of_device_node(device, mountinfo, monkeypatch):
    block_targets = {"/kubelet/publish/pvc-1/pod-1"}
    monkeypatch.setattr(
        filesystem.utils,
        "_is_device_node",
        lambda path, rdev: path in block_targets,
    )
    mountinfo(
        "25 21 0:5 / /dev rw,nosuid shared:2 - devtmpfs udev rw,mode=755",
        "40 21 0:5 /loop1 /kubelet/publish/pvc-1/pod-1 rw shared:2 - devtmpfs udev rw",
        # Another file that happens to be named like the device
        "41 21 8:1 /data/loop1 /mnt/loop1 rw shared:1 - ext4 /dev/sda1 rw",
        "42 21 0:5 /loop2 /kubelet/publish/pvc-2/pod-1 rw shared:2 - devtmpfs udev rw",
    )

    assert get_mountpoints_for_device(device.as_posix()) == [
        "/kubelet/publish/pvc-1/pod-1"
    ]


def test_unmounted_device(device, mountinfo):
    mountinfo("21 1 8:1 / / rw,relatime shared:1 - ext4 /dev/sda1 rw")

    assert get_mountpoints_for_device(device.as_posix()) == []
