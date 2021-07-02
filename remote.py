from util import remote_fn


@remote_fn
def scrub(volume_id):
    import time
    import rawfile_util

    img_dir = rawfile_util.img_dir(volume_id)
    if not img_dir.exists():
        return

    now = time.time()
    deleted_at = now
    gc_at = now  # TODO: GC sensitive PVCs later
    rawfile_util.patch_metadata(volume_id, {"deleted_at": deleted_at, "gc_at": gc_at})
    rawfile_util.gc_if_needed(volume_id, dry_run=False)


@remote_fn
def init_rawfile(volume_id, size):
    import time
    import rawfile_util
    from volume_schema import LATEST_SCHEMA_VERSION
    from pathlib import Path

    from util import run
    from consts import RESOURCE_EXHAUSTED_EXIT_CODE

    if rawfile_util.get_capacity() < size:
        exit(RESOURCE_EXHAUSTED_EXIT_CODE)

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
        },
    )
    run(f"truncate -s {size} {img_file}")


@remote_fn
def expand_rawfile(volume_id, size):
    import rawfile_util

    from util import run
    from consts import RESOURCE_EXHAUSTED_EXIT_CODE

    img_file = rawfile_util.img_file(volume_id)
    size_inc = size - rawfile_util.metadata(volume_id)["size"]
    if size_inc <= 0:
        return
    if rawfile_util.get_capacity() < size_inc:
        exit(RESOURCE_EXHAUSTED_EXIT_CODE)

    rawfile_util.patch_metadata(
        volume_id,
        {"size": size},
    )
    run(f"truncate -s {size} {img_file}")
