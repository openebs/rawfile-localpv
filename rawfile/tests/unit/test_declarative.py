import declarative
import pytest
from declarative import mount, unmount


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


class FakeFileSystem:
    def __init__(self):
        self.mountpoint = None
        self.mount_options = None

    def mount(self, options=None):
        self.mount_options = options


@pytest.fixture
def fs_publish(tmp_path, monkeypatch):
    # A filesystem volume's device and the dir it gets published on
    tmp_path = tmp_path.resolve()
    device = tmp_path / "loop1"
    device.touch()
    target = tmp_path / "publish"
    target.mkdir()
    mounted = {}
    commands = []
    fs = FakeFileSystem()

    monkeypatch.setattr(
        declarative, "get_device_for_mountpoint", lambda mp: mounted.get(mp)
    )
    monkeypatch.setattr(declarative, "from_device", lambda dev: fs)
    monkeypatch.setattr(declarative, "run", lambda cmd, **_: commands.append(cmd))
    return device.as_posix(), target.as_posix(), mounted, commands, fs


def test_mount_readonly_filesystem_remounts_publish_readonly(fs_publish):
    device, target, _, commands, fs = fs_publish

    mount(device, target, readonly=True, options=["noatime"])

    # The device is mounted with the requested options, then only this mount
    # is flagged read-only: the staging mount shares the superblock
    assert fs.mountpoint == target
    assert fs.mount_options == ["noatime"]
    assert commands == [f"mount -o remount,bind,noatime,ro {target}"]


def test_mount_readonly_filesystem_overrides_rw_option(fs_publish):
    device, target, _, commands, _ = fs_publish

    mount(device, target, readonly=True, options=["rw"])

    assert commands == [f"mount -o remount,bind,rw,ro {target}"]


def test_mount_filesystem_without_readonly_stays_writable(fs_publish):
    device, target, _, commands, fs = fs_publish

    mount(device, target, readonly=False, options=["noatime"])

    assert fs.mount_options == ["noatime"]
    assert commands == []


def test_mount_readonly_filesystem_already_mounted_is_remounted(fs_publish):
    # A retry after a publish that mounted the device but failed to remount it
    device, target, mounted, commands, fs = fs_publish
    mounted[target] = device

    mount(device, target, readonly=True)

    assert fs.mount_options is None
    assert commands == [f"mount -o remount,bind,ro {target}"]


def test_mount_filesystem_already_mounted_is_noop(fs_publish):
    device, target, mounted, commands, fs = fs_publish
    mounted[target] = device

    mount(device, target, readonly=False)

    assert fs.mount_options is None
    assert commands == []
