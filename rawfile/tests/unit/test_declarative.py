from pathlib import Path

import declarative
import pytest
from declarative import mount, unmount
from utils.errors import InvalidDeviceForMountpointError


def test_unmount_missing_path_is_noop(tmp_path):
    unmount((tmp_path / "missing").as_posix())


def test_unmount_unmounted_dir_is_cleared(tmp_path):
    # A target path left behind after its mount was lost
    target = tmp_path / "mount"
    target.mkdir()

    unmount(target.as_posix(), clear_mountpoint=True)

    assert not target.exists()


def test_unmount_unmounted_dir_is_kept_without_clear(tmp_path):
    target = tmp_path / "mount"
    target.mkdir()

    unmount(target.as_posix(), clear_mountpoint=False)

    assert target.is_dir()


def test_unmount_unmounted_dir_with_data_is_not_removed(tmp_path):
    target = tmp_path / "mount"
    target.mkdir()
    (target / "data").write_text("keep me")

    with pytest.raises(OSError):
        unmount(target.as_posix(), clear_mountpoint=True)

    assert (target / "data").read_text() == "keep me"


def test_unmount_dir_removed_concurrently(tmp_path, monkeypatch):
    target = tmp_path / "mount"
    target.mkdir()

    # A concurrent teardown removes the dir right after unmount() saw it exists
    def removed_meanwhile(mountpoint):
        target.rmdir()

    monkeypatch.setattr(declarative, "get_device_for_mountpoint", removed_meanwhile)

    unmount(target.as_posix(), clear_mountpoint=True)

    assert not target.exists()


@pytest.fixture
def block_publish(tmp_path, monkeypatch):
    # A block volume's loop device and the file its node gets bind mounted on
    tmp_path = tmp_path.resolve()
    device = tmp_path / "loop1"
    device.touch()
    target = tmp_path / "publish"
    target.touch()
    device_numbers = {device: 0x701}

    def block_device_number(path):
        return device_numbers.get(Path(path).resolve())

    commands = []
    monkeypatch.setattr(declarative, "_block_device_number", block_device_number)
    monkeypatch.setattr(declarative, "run", lambda cmd, **kwargs: commands.append(cmd))
    return device, target, device_numbers, commands


def test_mount_block_volume(block_publish, monkeypatch):
    device, target, _, commands = block_publish
    monkeypatch.setattr(declarative, "get_device_for_mountpoint", lambda mp: None)

    mount(device.as_posix(), target.as_posix())

    assert commands == [f"mount -t none -o bind {device} {target}"]


def test_mount_block_volume_already_mounted(block_publish, monkeypatch):
    device, target, device_numbers, commands = block_publish
    # The node is bind mounted: the target is the device, findmnt shows its filesystem
    device_numbers[target] = device_numbers[device]
    monkeypatch.setattr(declarative, "get_device_for_mountpoint", lambda mp: "udev")

    mount(device.as_posix(), target.as_posix())

    assert commands == []


def test_mount_block_volume_over_another_device(block_publish, monkeypatch):
    device, target, device_numbers, commands = block_publish
    device_numbers[target] = 0x702
    monkeypatch.setattr(declarative, "get_device_for_mountpoint", lambda mp: "udev")

    with pytest.raises(InvalidDeviceForMountpointError, match="7:2"):
        mount(device.as_posix(), target.as_posix())

    assert commands == []
