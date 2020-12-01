from util import remote_fn


@remote_fn
def scrub(volume_id):
    import rawfile_util
    from util import run

    lv_path = rawfile_util.lv_path(volume_id)
    run(f"lvremove {lv_path}")


@remote_fn
def init_rawfile(volume_id, size):
    import rawfile_util
    from util import run

    lv_path = rawfile_util.lv_path(volume_id)
    if lv_path.exists():
        return
    run(
        f"lvcreate {rawfile_util.thinpool} --name {rawfile_util.prefix}.{volume_id} --virtualsize {size}b --thin"
    )


@remote_fn
def expand_rawfile(volume_id, size):
    import rawfile_util
    from util import run

    lv_path = rawfile_util.lv_path(volume_id)
    if rawfile_util.metadata(volume_id)["size"] >= size:
        return
    run(f"lvextend {lv_path} --size {size}b")


@remote_fn
def snapshot_rawfile(volume_id, snapshot_id):
    import rawfile_util
    from util import run

    lv_path = rawfile_util.lv_path(volume_id)
    run(f"lvcreate {lv_path} --snapshot --name {rawfile_util.prefix}.{snapshot_id}")
