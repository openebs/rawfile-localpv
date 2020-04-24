import json
from pathlib import Path

from consts import DATA_DIR


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
