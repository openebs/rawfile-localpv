import json
import os
import subprocess

from prometheus_client.core import REGISTRY
from prometheus_client.exposition import start_http_server


def path_stats(path):
    fs_stat = os.statvfs(path)
    return {
        "fs_size": fs_stat.f_frsize * fs_stat.f_blocks,
        "fs_free": fs_stat.f_frsize * fs_stat.f_bfree,
        "fs_files": fs_stat.f_files,
        "fs_files_free": fs_stat.f_ffree,
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
        f"findmnt --json --first-only --mountpoint {mountpoint}",
        shell=True,
        capture_output=True,
    )
    if res.returncode != 0:
        return None
    data = json.loads(res.stdout.decode().strip())
    return data["filesystems"][0]["source"]


class VolumeStatsCollector(object):
    def collect(self):
        return []


def expose_metrics():
    REGISTRY.register(VolumeStatsCollector())
    start_http_server(9100)
