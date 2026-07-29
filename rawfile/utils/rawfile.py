import json
import os
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any

from config import config
from consts import D_PERMS, F_PERMS, OWNER_UMASK

from utils.commands import run
from utils.errors import LoopDeviceAttachError, UnknownFileTypeError
from utils.fallocate import fallocate as linux_fallocate
from utils.logs import logger


class AccessType(Enum):
    mount = 1
    block = 2


def meta_dir(volume_id):
    return Path(f"{config.csi_driver.metadata_dir}/{volume_id}")


def meta_file(volume_id):
    return Path(f"{meta_dir(volume_id)}/disk.meta")


def meta_file_tmp(volume_id):
    return Path(f"{meta_dir(volume_id)}/disk.meta.tmp")


def lock_file(volume_id):
    return Path(f"{meta_dir(volume_id)}/disk.lock")


def metadata(volume_id) -> dict[str, Any]:
    return json.loads(meta_file(volume_id).read_text())


def metadata_or(volume_id):
    try:
        return metadata(volume_id)
    except FileNotFoundError:
        return {}


def img_file(volume_id):
    return Path(metadata(volume_id)["img_file"])


def snapshots_dir(volume_id: str, temporary: bool = False):
    from utils.volume_manager import manager as volume_manager

    meta = metadata(volume_id)
    if temporary:
        return Path(
            f"{volume_manager._get_volume_path(meta.get('storage_pool', config.csi_driver.default_pool), volume_id)}/snapshots/temp"
        )
    return Path(
        f"{volume_manager._get_volume_path(meta.get('storage_pool', config.csi_driver.default_pool), volume_id)}/snapshots"
    )


def img_size(volume_id) -> int:
    return metadata(volume_id)["size"]


@contextmanager
def _owner_umask():
    old_umask = os.umask(OWNER_UMASK)
    try:
        yield
    finally:
        os.umask(old_umask)  # Restore original umask


def update_metadata(volume_id: str, storage_pool: str, obj: dict) -> dict:
    update_permissions(volume_id, storage_pool)
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


def update_permissions(volume_id: str, storage_pool: str) -> None:
    from itertools import chain

    from utils.volume_manager import manager as volume_manager

    _img_dir = volume_manager._get_volume_path(storage_pool, volume_id)
    if not _img_dir.exists():
        return
    _img_dir.chmod(D_PERMS)
    # set permissions recursively on all files and dirs under the volume path
    # we go 3 levels deep to cover most cases (img file, snapshots, temp snapshots, etc.)
    for each in chain(
        _img_dir.glob("**/*"), _img_dir.glob("**/**/*"), _img_dir.glob("**/**/**/*")
    ):
        each.chmod(F_PERMS)


def patch_metadata(volume_id: str, storage_pool: str, obj: dict) -> dict:
    old_data = metadata_or(volume_id)
    new_data = {**old_data, **obj}
    return update_metadata(volume_id, storage_pool, new_data)


def truncate(img_file, size):
    """Create the disk image file with the specified size. for thin provisioning

    Set the umask to restrict permissions to the owner only
    """
    with _owner_umask(), open(img_file, "a+b") as f:
        f.truncate(size)
        os.fsync(f.fileno())


def fallocate(img_file, size):
    """Create the disk image file with the specified size. for thick provisioning

    Set the umask to restrict permissions to the owner only
    """
    with _owner_umask(), open(img_file, "a+b") as f:
        linux_fallocate(f.fileno(), 0, 0, size)
        os.fsync(f.fileno())


def attached_loops(file: str) -> list[str]:
    out = run(f"losetup -j {file}", capture_output=True, log=False).stdout.decode()
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
    last_exception = None
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
        raise LoopDeviceAttachError(
            file, max_attempts, last_exception
        ) from last_exception
    else:
        raise LoopDeviceAttachError(file, max_attempts)


def detach_loops(file) -> None:
    devs = attached_loops(file)
    for dev in devs:
        run(f"losetup -d {dev}")


def be_absent(path):
    path = Path(path)
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        path.rmdir()
        # XXX: should we `shutil.rmtree(path)` instead?
    elif not path.exists():
        return
    else:
        raise UnknownFileTypeError(path)


def be_symlink(path, to):
    path = Path(path)
    to = Path(to)
    if path.is_symlink() and os.readlink(path) == str(to):
        return
    be_absent(path)
    path.symlink_to(to)


def is_cow_supported(source_dir: Path, destination_dir: Path) -> bool:
    """Check if the filesystem at the given directory supports copy-on-write (COW) operations.

    This function attempts to create a temporary file in the specified directory,
    then creates a reflink (COW clone) of that file. If the operation is successful,
    it indicates that the filesystem supports COW.

    Args:
        dir (Path): The directory to check for COW support.

    Returns:
        bool: True if COW is supported, False otherwise.
    """
    test_file = source_dir / ".cow_test_file"
    clone_file = destination_dir / ".cow_test_clone"
    try:
        with open(test_file, "wb") as f:
            f.write(b"COW Support Test")
            f.flush()
            os.fsync(f.fileno())
        run(f"cp --reflink=always {test_file} {clone_file}")
        return True
    except Exception as e:
        logger.opt(exception=e).warning("COW test failed")
        return False
    finally:
        be_absent(test_file)
        be_absent(clone_file)
