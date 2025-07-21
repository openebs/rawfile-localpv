from pathlib import Path
from filesystem import from_device
from filesystem.base import UnknownFileSystemError
from filesystem.utils import get_device_for_mountpoint
from utils.errors import (
    InvalidDeviceForMountpointError,
    UnknownDeviceForMountpointError,
)
from utils.commands import run
from copy import deepcopy


def mount(device, mountpoint, readonly=False, options: list[str] = []):
    current_dev = get_device_for_mountpoint(mountpoint)
    device = Path(device).resolve().as_posix()
    _options = deepcopy(options)

    if current_dev:
        current_dev = Path(current_dev).resolve().as_posix()
        if current_dev == device:
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
    # FIXME: RO mount for filesystems ignored (https://github.com/openebs/rawfile-localpv/pull/86#issuecomment-3000864823)
    # if readonly:
    #     _options.extend(["ro"])
    fs.mount(options=_options)


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
        raise UnknownDeviceForMountpointError(mountpoint=mountpoint)
    fs = from_device(device=device)
    if not fs:
        raise UnknownFileSystemError(device=device)
    fs.mountpoint = mountpoint
    fs.unmount(clear_mountpoint=clear_mountpoint)
