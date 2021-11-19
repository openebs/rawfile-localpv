from util import remote_fn


def scrub(volume_id):
    import time
    from subprocess import CalledProcessError

    import rawfile_util
    from consts import VOLUME_IN_USE_EXIT_CODE

    img_dir = rawfile_util.img_dir(volume_id)
    if not img_dir.exists():
        return

    img_file = rawfile_util.img_file(volume_id)
    loops = rawfile_util.attached_loops(img_file)
    if len(loops) > 0:
        raise CalledProcessError(returncode=VOLUME_IN_USE_EXIT_CODE, cmd="")

    now = time.time()
    deleted_at = now
    gc_at = now  # TODO: GC sensitive PVCs later
    rawfile_util.patch_metadata(volume_id, {"deleted_at": deleted_at, "gc_at": gc_at})
    rawfile_util.gc_if_needed(volume_id, dry_run=False)


def init_rawfile(volume_id, size):
    import time
    from subprocess import CalledProcessError
    from pathlib import Path

    import rawfile_util
    from volume_schema import LATEST_SCHEMA_VERSION
    from util import run
    from consts import RESOURCE_EXHAUSTED_EXIT_CODE

    if rawfile_util.get_capacity() < size:
        raise CalledProcessError(returncode=RESOURCE_EXHAUSTED_EXIT_CODE, cmd="")

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


def get_capacity():
    import rawfile_util

    cap = rawfile_util.get_capacity()
    return max(0, cap)


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
