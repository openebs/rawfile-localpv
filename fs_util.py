import json
import os
import subprocess


def path_stats(path):
    fs_stat = os.statvfs(path)
    return {
        "fs_size": fs_stat.f_frsize * fs_stat.f_blocks,
        "fs_avail": fs_stat.f_frsize * fs_stat.f_bavail,
        "fs_files": fs_stat.f_files,
        "fs_files_avail": fs_stat.f_favail,
    }


def device_stats(dev):
    output = subprocess.run(
        f"blockdev --getsize64 {dev}", shell=True, check=True, capture_output=True
    ).stdout.decode()
    dev_size = int(output)
    return {"dev_size": dev_size}


def dev_to_mountpoint(dev_name):
    try:
        output = subprocess.run(
            f"findmnt --json --first-only {dev_name}",
            shell=True,
            check=True,
            capture_output=True,
        ).stdout.decode()
        data = json.loads(output)
        return data["filesystems"][0]["target"]
    except subprocess.CalledProcessError:
        return None


def mountpoint_to_dev(mountpoint):
    res = subprocess.run(
        f"findmnt --json --first-only --nofsroot --mountpoint {mountpoint}",
        shell=True,
        capture_output=True,
    )
    if res.returncode != 0:
        return None
    data = json.loads(res.stdout.decode().strip())
    return data["filesystems"][0]["source"]
