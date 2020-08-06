from util import remote_fn


@remote_fn
def scrub(volume_id):
    import time
    import rawfile_util

    rawfile_util.patch_metadata(volume_id, {"deleted_at": time.time()})


@remote_fn
def init_rawfile(volume_id, size, fs_type):
    import time
    import rawfile_util
    from volume_schema import LATEST_SCHEMA_VERSION
    from pathlib import Path

    from util import run

    img_dir = rawfile_util.img_dir(volume_id)
    img_dir.mkdir(exist_ok=True)
    img_file = Path(f"{img_dir}/disk.img")
    if img_file.exists():
        return
    rawfile_util.patch_metadata(
        volume_id,
        {
            "schema_version": LATEST_SCHEMA_VERSION,
            "volume_id": volume_id,
            "created_at": time.time(),
            "img_file": img_file.as_posix(),
            "size": size,
            "fs_type": fs_type,
        },
    )
    run(f"truncate -s {size} {img_file}")
    if fs_type == "ext4":
        run(f"mkfs.ext4 {img_file}")
    elif fs_type == "xfs":
        run(f"mkfs.xfs {img_file}")
    elif fs_type == "btrfs":
        run(f"mkfs.btrfs {img_file}")
    else:
        raise Exception(f"Unsupported fsType: {fs_type}")


@remote_fn
def expand_rawfile(volume_id, size):
    import rawfile_util
    from util import run

    img_file = rawfile_util.img_file(volume_id)
    if rawfile_util.metadata(volume_id)["size"] >= size:
        return
    rawfile_util.patch_metadata(
        volume_id, {"size": size},
    )
    run(f"truncate -s {size} {img_file}")
