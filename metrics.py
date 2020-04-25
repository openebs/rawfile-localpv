import json
import os
import threading
from os.path import basename

from prometheus_client import Gauge
from prometheus_client.exposition import start_http_server

import rawfile_util
from rawfile_util import attached_loops
from util import run_out

VOLUME_ID = "volume_id"

fs_size = Gauge(
    "rawfile_filesystem_size_bytes", "Filesystem size in bytes.", [VOLUME_ID]
)
fs_free = Gauge(
    "rawfile_filesystem_avail_bytes", "Filesystem free space in bytes", [VOLUME_ID]
)
dev_size = Gauge("rawfile_device_size_bytes", "Device size in bytes.", [VOLUME_ID])
dev_free = Gauge(
    "rawfile_device_free_bytes", "Device free space in bytes.", [VOLUME_ID]
)


def collect_stats():
    blockdevices = json.loads(run_out("lsblk --json").stdout.decode())["blockdevices"]

    def dev_to_mountpoint(dev_name):
        dev_name = basename(dev_name)
        matches = list(filter(lambda bd: bd["name"] == dev_name, blockdevices))
        if len(matches) == 0:
            return None
        return matches[0]["mountpoint"]

    for volume_id in rawfile_util.list_all_volumes():
        img_file = rawfile_util.img_file(volume_id)
        labels = {VOLUME_ID: volume_id}
        dev_stat = img_file.stat()
        dev_size.labels(**labels).set(dev_stat.st_size)
        dev_free.labels(**labels).set(
            dev_stat.st_size - dev_stat.st_blocks * dev_stat.st_blksize
        )
        for dev in attached_loops(img_file):
            mountpoint = dev_to_mountpoint(dev)
            if mountpoint is None:
                continue
            fs_stat = os.statvfs(mountpoint)
            fs_size.labels(**labels).set(fs_stat.f_frsize * fs_stat.f_blocks)
            fs_free.labels(**labels).set(fs_stat.f_frsize * fs_stat.f_bfree)
            break


def expose_metrics():
    def collector_loop():
        collect_stats()
        threading.Timer(10, collector_loop).start()

    collector_loop()
    start_http_server(9100)
