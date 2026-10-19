import declarative
import pytest
from declarative import unmount


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
