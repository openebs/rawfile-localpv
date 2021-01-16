import os
from pathlib import Path

from util import run


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


def be_mounted(dev, mountpoint):
    dev = Path(dev).resolve()
    mountpoint = Path(mountpoint)

    if mountpoint.is_mount():
        if True:  # TODO: verify that the right device is mounted
            return
        # noinspection PyUnreachableCode
        be_unmounted(mountpoint)

    run(f"mount {dev} {mountpoint}")


def be_unmounted(path):
    path = Path(path)
    while path.is_mount():
        run(f"umount {path}")
