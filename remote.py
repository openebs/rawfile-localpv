from util import remote_fn


@remote_fn
def scrub(volume_id):
    # TODO: stub
    pass


@remote_fn
def init_rawfile(volume_id, size):
    from util import run
    from consts import DATA_DIR
    from pathlib import Path

    img_dir = Path(f"{DATA_DIR}/{volume_id}")
    img_dir.mkdir(parents=False, exist_ok=False)
    img_file = Path(f"{img_dir}/raw.img")
    run(f"truncate -s {size} {img_file}")
    run(f"mkfs.ext4 {img_file}")
