import json
from pathlib import Path

from consts import DATA_DIR
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


def patch_metadata(volume_id, obj):
    old_data = metadata(volume_id)
    new_data = {**old_data, **obj}
    meta_file(volume_id).write_text(json.dumps(new_data))
    return new_data


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
