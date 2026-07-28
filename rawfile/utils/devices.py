import json
import os
import subprocess
from pathlib import Path

from utils.commands import run


def statvfs(path):
    fs_stat = os.statvfs(path)

    total = fs_stat.f_frsize * fs_stat.f_blocks
    avail = fs_stat.f_frsize * fs_stat.f_bavail
    # FIXME (pgu, 09.02.2026): this is not necessarily true in the sense that
    # f_bavail shows blocks available to non-privileged users; hence usage will
    # implicitly include all the blocks reserved for priviliged users in the
    # stats
    usage = total - avail

    return {
        "fs_size": total,
        "fs_avail": avail,
        "fs_usage": usage,
        "fs_files": fs_stat.f_files,
        "fs_files_avail": fs_stat.f_favail,
        "fs_id": fs_stat.f_fsid,
    }


def stat(filepath):
    stat = os.stat(filepath)

    return {
        "logical_size": stat.st_size,
        "physical_size": stat.st_blocks * 512,
        "dev": stat.st_dev,
    }


def device_stats(dev):
    output = run(
        f"blockdev --getsize64 {dev}", check=True, capture_output=True
    ).stdout.decode()
    dev_size = int(output)
    return {"dev_size": dev_size}


def device_to_mountpoint(
    device: str, first_only: bool = True
) -> None | str | list[str]:
    try:
        output = run(
            f"findmnt --json {'--first-only' if first_only else ''} {device}",
            check=True,
            capture_output=True,
        ).stdout.decode()
        data = json.loads(output)
        return (
            data["filesystems"][0]["target"]
            if first_only
            else [fs["target"] for fs in data["filesystems"]]
        )
    except subprocess.CalledProcessError:
        return None


def mountpoint_to_dev(mountpoint) -> str | None:
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
