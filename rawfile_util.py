vg = "vg-test"
prefix = "ngpv"
thinpool = f"{vg}/tpool"


def metadata(volume_id):
    # TODO
    # f"lvs {vg}/{volume_id} --reportformat json"
    return {"size": 0}


def lv_path(volume_id):
    return f"/dev/{vg}/{prefix}.{volume_id}"
