from contextlib import suppress
from copy import deepcopy
from pathlib import Path

from filesystem import from_device
from filesystem.base import UnknownFileSystemError
from filesystem.utils import get_device_for_mountpoint
from utils.commands import run
from utils.errors import InvalidDeviceForMountpointError


def remount_readonly(mountpoint: str, options: list[str] | None = None):
    # The filesystem is already mounted read-write on the staging path, and a
    # superblock can't be mounted both ways ("already mounted" error), so only
    # flag this mount read-only. The volume's options are passed again so their
    # per-mount flags (e.g. nosuid) aren't reset, with "ro" last to win over "rw".
    opts_str = ",".join(["remount", "bind", *(options or []), "ro"])
    run(f"mount -o {opts_str} {mountpoint}")


def mount(device, mountpoint, readonly=False, options: list[str] | None = None):
    current_dev = get_device_for_mountpoint(mountpoint)
    device = Path(device).resolve().as_posix()
    _options = deepcopy(options)
    _options = _options or []

    if current_dev:
        current_dev = Path(current_dev).resolve().as_posix()
        if current_dev == device:
            # A retry may follow a publish that failed before its remount
            if readonly and Path(mountpoint).resolve().is_dir():
                remount_readonly(mountpoint, _options)
            return  # TODO: LOG
        raise InvalidDeviceForMountpointError(device=current_dev, mountpoint=mountpoint)

    if Path(mountpoint).resolve().is_file():
        _options.append("bind")
        # TODO: this is not sufficient,
        # we need to create a separate loop device for RO
        if readonly:
            _options.append("ro")
        opts_str = ",".join(_options)
        run(f"mount -t none -o {opts_str} {device} {mountpoint}")
        return
    fs = from_device(device)
    if not fs:
        raise UnknownFileSystemError(device=device)
    fs.mountpoint = mountpoint
    fs.mount(options=_options)
    if readonly:
        remount_readonly(mountpoint, _options)


def unmount(mountpoint: str, clear_mountpoint=True):
    path = Path(mountpoint)
    if not path.exists():
        return
    if path.is_file() or path.is_block_device():
        run(
            f"umount {mountpoint}",
            check=True,
            capture_output=True,
        )
        if clear_mountpoint:
            path.unlink(missing_ok=True)
        return
    device = get_device_for_mountpoint(mountpoint)
    if not device:
        # Nothing is mounted here (e.g. the mount was lost on a restart): treat it
        # as already unmounted, as CSI requires NodeUnpublish/NodeUnstage to be
        # idempotent. rmdir fails on a non-empty dir, so no data is removed; a
        # concurrent teardown may have removed the dir since the exists() check.
        if clear_mountpoint:
            with suppress(FileNotFoundError):
                path.rmdir()
        return
    fs = from_device(device=device)
    if not fs:
        raise UnknownFileSystemError(device=device)
    fs.mountpoint = mountpoint
    fs.unmount(clear_mountpoint=clear_mountpoint)
