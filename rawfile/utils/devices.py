from pydantic import ByteSize
from utils.commands import run
import os
import subprocess
import json
from pathlib import Path


def path_stats(path, capacity_override: ByteSize | None = None):
    fs_stat = os.statvfs(path)

    total = fs_stat.f_frsize * fs_stat.f_blocks
    if capacity_override:
        total = capacity_override.to("B")
    avail = fs_stat.f_frsize * fs_stat.f_bavail
    usage = total - avail

    return {
        "fs_size": total,
        "fs_avail": total - usage,
        "fs_usage": usage,
        "fs_files": fs_stat.f_files,
        "fs_files_avail": fs_stat.f_favail,
    }


def device_stats(dev):
    output = run(
        f"blockdev --getsize64 {dev}", check=True, capture_output=True
    ).stdout.decode()
    dev_size = int(output)
    return {"dev_size": dev_size}


def device_to_mountpoint(device: str) -> None | str:
    try:
        output = run(
            f"findmnt --json --first-only {device}",
            check=True,
            capture_output=True,
        ).stdout.decode()
        data = json.loads(output)
        return data["filesystems"][0]["target"]
    except subprocess.CalledProcessError:
        return None


def mountpoint_to_dev(mountpoint):
    assert Path(mountpoint).is_dir()
    res = run(
        f"findmnt --json --first-only --nofsroot --mountpoint {mountpoint}",
        capture_output=True,
        check=False,
    )
    if res.returncode != 0:
        return None
    data = json.loads(res.stdout.decode().strip())
    return data["filesystems"][0]["source"]
