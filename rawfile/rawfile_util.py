import glob
import json
import time
from contextlib import contextmanager
from os import umask
from os.path import basename, dirname
from pathlib import Path

from consts import D_PERMS, DATA_DIR, F_PERMS, OWNER_UMASK
from declarative import be_absent
from fs_util import path_stats
from util import run, run_out
from volume_schema import LATEST_SCHEMA_VERSION, migrate_to


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
        meta_file(volume_id).write_text(json.dumps(obj))
    return obj


def update_permissions(volume_id: str) -> None:
    _img_dir = img_dir(volume_id)
    if not _img_dir.exists():
        return
    _img_dir.chmod(D_PERMS)
    for each in _img_dir.glob("**/*"):
        each.chmod(F_PERMS)


def patch_metadata(volume_id: str, obj: dict) -> dict:
    old_data = metadata(volume_id)
    new_data = {**old_data, **obj}
    return update_metadata(volume_id, new_data)


def migrate_metadata(volume_id, target_version):
    old_data = metadata(volume_id)
    new_data = migrate_to(old_data, target_version)
    return update_metadata(volume_id, new_data)


def truncate(img_file, size):
    """Create the disk image file with the specified size.

    Set the umask to restrict permissions to the owner only
    """
    with _owner_umask():
        run(f"truncate -s {size} {img_file}")


def attached_loops(file: str) -> list[str]:
    out = run_out(f"losetup -j {file}").stdout.decode()
    lines = out.splitlines()
    devs = [line.split(":", 1)[0] for line in lines]
    return devs


def attach_loop(file) -> str:
    def next_loop():
        loop_file = run_out("losetup -f").stdout.decode().strip()
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
