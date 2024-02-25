import json
import uuid
from pathlib import Path
from subprocess import CalledProcessError
from time import sleep

import pykube
import yaml
from munch import Munch

from consts import CONFIG

api = pykube.HTTPClient(pykube.KubeConfig.from_env())


def volume_to_node(volume_id):
    pv = pykube.PersistentVolume.objects(api).get_by_name(name=volume_id)
    pv = Munch.fromDict(pv.obj)
    node_name = pv.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0][
        "values"
    ][0]
    expected_node_affinity = yaml.safe_load(
        f"""
required:
  nodeSelectorTerms:
  - matchExpressions:
    - key: hostname
      operator: In
      values:
      - {node_name}
    """
    )
    assert pv.spec.nodeAffinity == expected_node_affinity
    return node_name


def wait_for(pred, desc=""):
    print(f"Waiting for {desc}", end="", flush=True)
    while not pred():
        print(".", end="", flush=True)
        sleep(0.5)
    print(" done")


def run_on_node(fn, node):
    name = f"task-{uuid.uuid4()}"
    ctx = {
        "name": name,
        "namespace": "kube-system",  # FIXME
        "nodeSelector": json.dumps({"kubernetes.io/hostname": node}),
        "cmd": json.dumps(fn),
        "image_repository": CONFIG["image_repository"],
        "image_tag": CONFIG["image_tag"],
        "datadir": CONFIG["node_datadir"]
    }
    template = Path("./templates/task.yaml").read_bytes().decode()
    manifest = template.format(**ctx)
    obj = yaml.safe_load(manifest)
    task_pod = pykube.Pod(api, obj)
    task_pod.create()

    def is_finished():
        task_pod.reload()
        status = task_pod.obj["status"]
        if status["phase"] in ["Succeeded", "Failed"]:
            return True
        return False

    wait_for(is_finished, "task to finish")
    task_pod.delete()
    if task_pod.obj["status"]["phase"] != "Succeeded":
        exit_code = task_pod.obj["status"]["containerStatuses"][0]["state"][
            "terminated"
        ]["exitCode"]
        raise CalledProcessError(returncode=exit_code, cmd=f"Task: {name}")
