import glob
import json
import time
from contextlib import contextmanager
from os import umask
from os.path import basename, dirname
from pathlib import Path
from typing import Any

from utils.logs import logger

from consts import D_PERMS, DATA_DIR, F_PERMS, OWNER_UMASK
from volume_schema import LATEST_SCHEMA_VERSION, migrate_to
import os
from enum import Enum
from utils.commands import run
from utils.fallocate import fallocate as linux_fallocate
from utils.devices import path_stats, device_to_mountpoint
from config import config


class AccessType(Enum):
    mount = 1
    block = 2


def img_dir(volume_id):
    return Path(f"{DATA_DIR}/{volume_id}")


def meta_file(volume_id):
    return Path(f"{img_dir(volume_id)}/disk.meta")


def meta_file_tmp(volume_id):
    return Path(f"{img_dir(volume_id)}/disk.meta.tmp")


def lock_file(volume_id):
    return Path(f"{img_dir(volume_id)}/disk.lock")


def metadata(volume_id) -> dict[str, Any]:
    return json.loads(meta_file(volume_id).read_text())


def metadata_or(volume_id):
    try:
        return metadata(volume_id)
    except FileNotFoundError:
        return {}


def img_file(volume_id):
    return Path(metadata(volume_id)["img_file"])


def img_size(volume_id) -> int:
    return metadata(volume_id)["size"]


def destroy(volume_id, dry_run=True):
    logger.info("Destroying Volume", volume_id=volume_id, dry_run=dry_run)
    if not dry_run:
        Path(img_file(volume_id)).unlink(missing_ok=True)
        Path(meta_file(volume_id)).unlink(missing_ok=True)
        Path(lock_file(volume_id)).unlink(missing_ok=True)
        try:
            Path(img_dir(volume_id)).rmdir()
        except FileNotFoundError:
            pass


def gc_if_needed(volume_id, dry_run=True):
    meta = metadata_or(volume_id)

    deleted_at = meta.get("deleted_at", None)
    gc_at = meta.get("gc_at", None)
    if deleted_at is None or gc_at is None:
        return False

    now = time.time()
    if gc_at <= now:
        destroy(volume_id, dry_run=dry_run)

    return False


@contextmanager
def _owner_umask():
    old_umask = umask(OWNER_UMASK)
    try:
        yield
    finally:
        umask(old_umask)  # Restore original umask


def update_metadata(volume_id: str, obj: dict) -> dict:
    update_permissions(volume_id)
    with _owner_umask():
        meta_tmp = meta_file_tmp(volume_id)
        meta = meta_file(volume_id)

        with meta_tmp.open(mode="w", encoding="utf-8") as f:
            json.dump(obj, f)
            f.flush()
            os.fsync(f.fileno())

        os.replace(meta_tmp, meta)
        # fsync the directory to persist the rename
        dir_fd = os.open(str(meta.parent), os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    return obj


def update_permissions(volume_id: str) -> None:
    _img_dir = img_dir(volume_id)
    if not _img_dir.exists():
        return
    _img_dir.chmod(D_PERMS)
    for each in _img_dir.glob("**/*"):
        each.chmod(F_PERMS)


def patch_metadata(volume_id: str, obj: dict) -> dict:
    old_data = metadata_or(volume_id)
    new_data = {**old_data, **obj}
    return update_metadata(volume_id, new_data)


def migrate_metadata(volume_id, target_version):
    old_data = metadata_or(volume_id)
    new_data = migrate_to(old_data, target_version)
    return update_metadata(volume_id, new_data)


def truncate(img_file, size):
    """Create the disk image file with the specified size. for thin provisioning

    Set the umask to restrict permissions to the owner only
    """
    with _owner_umask():
        with open(img_file, "a+b") as f:
            f.truncate(size)
            os.fsync(f.fileno())


def fallocate(img_file, size):
    """Create the disk image file with the specified size. for thick provisioning

    Set the umask to restrict permissions to the owner only
    """
    with _owner_umask():
        with open(img_file, "a+b") as f:
            linux_fallocate(f.fileno(), 0, 0, size)
            os.fsync(f.fileno())


def attached_loops(file: str) -> list[str]:
    out = run(f"losetup -j {file}", capture_output=True).stdout.decode()
    lines = out.splitlines()
    devs = [line.split(":", 1)[0] for line in lines]
    return devs


def attach_loop(file) -> str:
    def next_loop():
        loop_file = run("losetup -f", capture_output=True).stdout.decode().strip()
        if not Path(loop_file).exists():
            pfx_len = len("/dev/loop")
            loop_dev_id = loop_file[pfx_len:]
            run(f"mknod {loop_file} b 7 {loop_dev_id}")
        return loop_file

    # if multiple pods are getting staged at the same time, and there's not enough loop nodes, then we
    # could clash on the creation, thus leading into losetup -f failures...
    max_attempts = 20
    for _ in range(max_attempts):
        try:
            devs = attached_loops(file)
            if len(devs) > 0:
                # we could use -L to ensure there's no overlap, and thus having
                # only 1 device at most a match and allowing us to simply use
                # losetup --direct-io=on -fL --show {file}
                dev = devs[0]
                # sometimes a RO attribute is sticky on the loop device, for some reason
                run(f"blockdev --setrw {dev}")
                return dev
            next_loop()
            run(f"losetup --direct-io=on -f {file}")
        except Exception as e:
            # todo: add some jitter here?
            last_exception = e

    if last_exception:
        raise Exception(
            f"Failed to attach loop device for {file} after {max_attempts} attempts: {last_exception}"
        )
    else:
        raise Exception(
            f"Failed to attach loop device for {file} after {max_attempts} attempts"
        )


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


def get_volumes_stats() -> dict[str, dict[str, int]]:
    volumes_stats = {}
    for volume_id in list_all_volumes():
        try:
            file = img_file(volume_id=volume_id)
            loop_devs = attached_loops(file.as_posix())
            if not (loop_devs and len(loop_devs)):
                continue
            mountpoint = device_to_mountpoint(loop_devs[0])
            if not mountpoint:
                continue
            stats = path_stats(mountpoint)
            volumes_stats[volume_id] = {
                "used": stats["fs_usage"],
                "total": stats["fs_size"],
            }
        except FileNotFoundError:
            pass
    return volumes_stats


def get_capacity():
    disk_free_size = path_stats(DATA_DIR, config.capacity_override)["fs_avail"]
    capacity = disk_free_size
    for volume_stat in get_volumes_stats().values():
        capacity -= volume_stat["total"] - volume_stat["used"]
    if isinstance(config.reserved_capacity, str):
        capacity -= capacity * int(config.reserved_capacity[:-1]) / 100
    else:
        capacity -= config.reserved_capacity.to("B")
    return max(capacity, 0)


def be_absent(path):
    path = Path(path)
    if path.is_symlink():
        path.unlink()
    elif path.is_file():
        path.unlink()
    elif path.is_dir():
        path.rmdir()
        # XXX: should we `shutil.rmtree(path)` instead?
    elif not path.exists():
        return
    else:
        raise Exception("Unknown file type")


def be_symlink(path, to):
    path = Path(path)
    to = Path(to)
    if path.is_symlink():
        if os.readlink(path) == str(to):
            return
    be_absent(path)
    path.symlink_to(to)
