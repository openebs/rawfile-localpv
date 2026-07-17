import re
import subprocess
from pathlib import Path
from utils.commands import run


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
