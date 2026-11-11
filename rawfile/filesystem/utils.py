import os
import re
import stat
import subprocess
from pathlib import Path

from utils.commands import run

MOUNTINFO = "/proc/self/mountinfo"


def get_device_fs(device: str) -> str | None:
    res = run(f"blkid -o value -s TYPE {device}", capture_output=True, check=False)
    if res.returncode == 2:  # specified token was not found
        return None

    return res.stdout.decode().strip()


def get_device_for_mountpoint(mountpoint: str) -> str | None:
    try:
        output = run(
            f"findmnt -no SOURCE --mountpoint {mountpoint}",
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        return None
    source = output.stdout.decode().strip()
    if not source:
        return None
    # Strip bind-mount subpath notation, "/dev/loop1[/default]" -> "/dev/loop1"
    device = re.sub(r"\[.*\]$", "", source)
    return Path(device).resolve().as_posix()


def _unescape_mountinfo(field: str) -> str:
    # mountinfo escapes space, tab, newline and backslash in octal, e.g. "\040"
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), field)


def _is_device_node(path: str, rdev: int) -> bool:
    try:
        st = os.stat(path)
    except OSError:
        return False
    return stat.S_ISBLK(st.st_mode) and st.st_rdev == rdev


def get_mountpoints_for_device(device: str) -> list[str]:
    """
    List where `device` is mounted: the mounts of the filesystem on it, and the
    bind mounts of the device node itself, which is how block volumes are
    published.
    """
    device_path = Path(device).resolve()
    rdev = device_path.stat().st_rdev
    mountpoints = []
    with open(MOUNTINFO) as mountinfo:
        for line in mountinfo:
            # <id> <parent> <major:minor> <root> <mountpoint> <options>
            # [<optional fields>...] - <fstype> <source> <super options>
            fields = line.split()
            separator = fields.index("-", 6)
            root = _unescape_mountinfo(fields[3])
            mountpoint = _unescape_mountinfo(fields[4])
            source = _unescape_mountinfo(fields[separator + 2])
            filesystem_mount = source == device_path.as_posix()
            # A bind mount of the device node has the node's path in /dev as root
            device_node_bind = Path(root).name == device_path.name and (
                _is_device_node(mountpoint, rdev)
            )
            if filesystem_mount or device_node_bind:
                mountpoints.append(mountpoint)
    return mountpoints
