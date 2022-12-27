import glob
import json
from os.path import basename, dirname
from os import listdir, major, minor
from pathlib import Path
from psutil import disk_partitions, disk_usage
import time

from consts import DATA_DIR, PROVISIONER_NAME
from declarative import be_absent
from fs_util import path_stats
from volume_schema import migrate_to, LATEST_SCHEMA_VERSION
from util import run, run_out


def img_dir(volume_id):
    return Path(f"{DATA_DIR}/{volume_id}")


def meta_file(volume_id):
    return Path(f"{img_dir(volume_id)}/disk.meta")


def metadata(volume_id):
    try:
        return json.loads(meta_file(volume_id).read_text())
    except FileNotFoundError:
        return {}


def img_file(volume_id):
    return Path(metadata(volume_id)["img_file"])


def destroy(volume_id, dry_run=True):
    print(f"Destroying {volume_id}")
    if not dry_run:
        be_absent(img_file(volume_id))
        be_absent(meta_file(volume_id))
        be_absent(img_dir(volume_id))


def gc_if_needed(volume_id, dry_run=True):
    meta = metadata(volume_id)

    deleted_at = meta.get("deleted_at", None)
    gc_at = meta.get("gc_at", None)
    if deleted_at is None or gc_at is None:
        return False

    now = time.time()
    if gc_at <= now:
        destroy(volume_id, dry_run=dry_run)

    return False


def update_metadata(volume_id: str, obj: dict) -> dict:
    meta_file(volume_id).write_text(json.dumps(obj))
    return obj


def patch_metadata(volume_id: str, obj: dict) -> dict:
    old_data = metadata(volume_id)
    new_data = {**old_data, **obj}
    return update_metadata(volume_id, new_data)


def migrate_metadata(volume_id, target_version):
    old_data = metadata(volume_id)
    new_data = migrate_to(old_data, target_version)
    return update_metadata(volume_id, new_data)


def attached_loops(file: str) -> [str]:
    out = run_out(f"losetup -j {file}").stdout.decode()
    lines = out.splitlines()
    devs = [line.split(":", 1)[0] for line in lines]
    return devs


def attach_loop(file) -> str:
    def next_loop():
        loop_file = run_out(f"losetup -f").stdout.decode().strip()
        if not Path(loop_file).exists():
            pfx_len = len("/dev/loop")
            loop_dev_id = loop_file[pfx_len:]
            run(f"mknod {loop_file} b 7 {loop_dev_id}")
        return loop_file

    while True:
        devs = attached_loops(file)
        if len(devs) > 0:
            return devs[0]
        next_loop()
        run(f"losetup --direct-io=on -f {file}")


def detach_loops(file) -> None:
    devs = attached_loops(file)
    for dev in devs:
        run(f"losetup -d {dev}")


def list_all_volumes():
    metas = glob.glob(f"{DATA_DIR}/*/disk.meta")
    return [basename(dirname(meta)) for meta in metas]


def migrate_all_volume_schemas():
    target_version = LATEST_SCHEMA_VERSION
    for volume_id in list_all_volumes():
        migrate_metadata(volume_id, target_version)


def gc_all_volumes(dry_run=True):
    for volume_id in list_all_volumes():
        gc_if_needed(volume_id, dry_run=dry_run)


def get_volumes_stats() -> [dict]:
    volumes_stats = {}
    for volume_id in list_all_volumes():
        file = img_file(volume_id=volume_id)
        stats = file.stat()
        volumes_stats[volume_id] = {
            "used": stats.st_blocks * 512,
            "total": stats.st_size,
        }
    return volumes_stats


def get_capacity():
    disk_free_size = path_stats(DATA_DIR)["fs_avail"]
    capacity = disk_free_size
    for volume_stat in get_volumes_stats().values():
        capacity -= volume_stat["total"] - volume_stat["used"]
    return capacity


def list_all_loops():
    loops = []
    loopdir = Path('/sys/devices/virtual/block/')
    if not loopdir.exists():
        return loops
    for vb in listdir(loopdir):
        bf = Path(f"/sys/devices/virtual/block/{vb}/loop/backing_file")
        bdi = Path(f"/sys/devices/virtual/block/{vb}/bdi").resolve()
        dev = Path(f"/dev/{vb}")
        if not bf.is_file() or not bdi.is_dir() or not dev.is_block_device():
            continue
        # loop stat
        rdev = dev.stat().st_rdev
        if f"{major(rdev)}:{minor(rdev)}" != bdi.name:
            continue
        loops.append({
            'name': str(dev),
            'back-file': bf.read_text().strip(),
        })
    return loops


def get_volumes_fs_stats() -> [dict]:
    # get all volumes
    volumes = {}
    for volume_id in list_all_volumes():
        volumes[str(img_file(volume_id))] = volume_id
    # get managed loops
    loops = {}
    all_loops = list_all_loops()
    for loop in all_loops:
        img = loop['back-file']
        # DATA_DIR prefix will miss in 'back-file' if csi-driver container is restarted
        if img.startswith('/pvc-') and not img.startswith(DATA_DIR):
            img = f"{DATA_DIR}{img}"
        if img in volumes:
            loops[loop['name']] = loop
    # get volumes fs
    volumes_fs_stats = {}
    parts = disk_partitions()
    for part in parts:
        if part.device in loops and PROVISIONER_NAME in part.mountpoint:
            pu = disk_usage(part.mountpoint)
            loop = loops[part.device]
            img = loop['back-file']
            if img.startswith('/pvc-') and not img.startswith(DATA_DIR):
                img = f"{DATA_DIR}{img}"
            volume_id = volumes[img]
            volumes_fs_stats[volume_id] = {
                # part info
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                # loop info
                "loop": loop['name'],
                "img": img,
                # fs info
                "total": pu.total,
                "used": pu.used,
                "free": pu.free,
            }
    return volumes_fs_stats
