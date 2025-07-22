from typing import Any, TypedDict
import uuid
import os
from subprocess import CalledProcessError
from time import sleep
import re
from datetime import datetime
from consts import VOLUME_IS_ATTACHED
from kubernetes import client as k8s_client, config as k8s_config
from config import config
from utils.logs import logger
from kubernetes.client.rest import ApiException


def load_config():
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        k8s_config.load_incluster_config()
    else:
        k8s_config.load_config()


load_config()


class TaskPodInfo(TypedDict):
    name: str
    namespace: str
    datadir: str
    node_selector: dict[str, str]
    image_repository: str
    image_tag: str
    command: str


def generate_task_pod_manifest(info: TaskPodInfo) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": info["name"], "namespace": info["namespace"]},
        "spec": {
            "restartPolicy": "Never",
            "terminationGracePeriodSeconds": 0,
            "tolerations": [{"operator": "Exists"}],
            "volumes": [
                {
                    "name": "data-dir",
                    "hostPath": {"path": info["datadir"], "type": "DirectoryOrCreate"},
                },
                {"name": "device", "hostPath": {"path": "/dev", "type": "Directory"}},
            ],
            "nodeSelector": info["node_selector"],
            "containers": [
                {
                    "name": "task",
                    "image": f"{info['image_repository']}:{info['image_tag']}",
                    "imagePullPolicy": "IfNotPresent",
                    "volumeMounts": [
                        {"name": "data-dir", "mountPath": "/data"},
                        {"name": "device", "mountPath": "/dev"},
                    ],
                    "resources": {
                        "requests": {"cpu": "0m", "memory": "0Mi"},
                        "limits": {"cpu": "100m", "memory": "100Mi"},
                    },
                    "command": ["/bin/sh", "-c"],
                    "args": [info["command"]],
                }
            ],
        },
    }


def volume_to_node(volume_id):
    api = k8s_client.CoreV1Api()
    pv: k8s_client.V1PersistentVolume = api.read_persistent_volume(name=volume_id)
    curr_node_affinity: k8s_client.V1VolumeNodeAffinity = pv.spec.node_affinity
    node_name = (
        curr_node_affinity.required.node_selector_terms[0]
        .match_expressions[0]
        .values[0]
    )
    expected_affinity = k8s_client.V1VolumeNodeAffinity(
        required=k8s_client.V1NodeSelector(
            [
                k8s_client.V1NodeSelectorTerm(
                    match_expressions=[
                        k8s_client.V1NodeSelectorRequirement(
                            key="hostname", operator="In", values=[node_name]
                        )
                    ]
                )
            ]
        )
    )
    assert curr_node_affinity == expected_affinity
    return node_name


def wait_for(pred, desc=""):
    start = datetime.now()
    while not pred():
        sleep(0.5)
    end = datetime.now()
    logger.info(
        f"Finished waiting for {desc}", start=start, end=end, latency=end - start
    )


def run_on_node(fn, node):
    api = k8s_client.CoreV1Api()
    name = f"task-{uuid.uuid4()}"
    registry = config.image_registry
    repository = config.image_repository
    ctx: TaskPodInfo = {
        "name": name,
        "namespace": config.namespace,
        "node_selector": {"kubernetes.io/hostname": node},
        "command": fn,
        "image_repository": (
            f"{registry}/{repository}" if registry is not None else repository
        ),
        "image_tag": config.image_tag,
        "datadir": config.node_datadir,
    }
    manifest = generate_task_pod_manifest(ctx)
    logger.debug("Creating task pod", manifest=manifest)
    api.create_namespaced_pod(
        namespace=config.namespace,
        body=manifest,
    )

    def is_finished():
        task_pod = api.read_namespaced_pod(name=name, namespace=config.namespace)
        status = task_pod.status
        if status.phase in ("Succeeded", "Failed"):
            return True
        return False

    wait_for(is_finished, "task to finish")
    task_pod = api.read_namespaced_pod(name=name, namespace=config.namespace)
    status = task_pod.status
    logs = api.read_namespaced_pod_log(
        name=name, namespace=config.namespace, container="task"
    )
    api.delete_namespaced_pod(name=name, namespace=config.namespace)

    if status.phase != "Succeeded":
        exit_code = status.container_statuses[0].state.terminated.exit_code
        logger.error(
            "Task failed", exit_code=exit_code, output=logs, pod_name=name, node=node
        )
        raise CalledProcessError(returncode=exit_code, cmd=f"Task: {name}", output=logs)

    match = re.search(f"{VOLUME_IS_ATTACHED}=(True|False)", logs)
    is_attached = match.group(1) == "True" if match else None
    return is_attached


def namespace_uid(namespace: str) -> str:
    v1 = k8s_client.CoreV1Api()
    namespace = v1.read_namespace(name=namespace)
    return namespace.metadata.uid


def version_code():
    version_api = k8s_client.VersionApi()
    return version_api.get_code()


def read_node_info(nodeid):
    v1 = k8s_client.CoreV1Api()
    node = v1.read_node(name=nodeid)
    info = node.status.node_info
    return info


def node_count() -> int:
    v1 = k8s_client.CoreV1Api()
    node_count = len(v1.list_node().items)
    return node_count


def read_config_map(name: str):
    v1 = k8s_client.CoreV1Api()
    try:
        config_map = v1.read_namespaced_config_map(name, namespace=config.namespace)
        return config_map.data or {}
    except ApiException as e:
        if e.status == 404:
            return {}
        raise e


def write_config_map(name: str, key: str, value: str, overwrite=False):
    v1 = k8s_client.CoreV1Api()
    namespace = config.namespace

    try:
        config_map = v1.read_namespaced_config_map(name, namespace)
        data = config_map.data or {}

        if key not in data:
            data[key] = value
            config_map.data = data
            v1.replace_namespaced_config_map(name, namespace, body=config_map)
            logger.trace("Added key", name=name, key=key, value=value)
        elif overwrite:
            data[key] = value
            config_map.data = data
            v1.replace_namespaced_config_map(name, namespace, body=config_map)
            logger.trace("Modified key", name=name, key=key, value=value, old=data[key])
        else:
            logger.trace(
                "Not modifying existing key",
                name=name,
                key=key,
                value=value,
                old=data[key],
            )

    except ApiException as e:
        if e.status == 404:
            logger.trace("Creating new configmap", name=name, key=key, value=value)
            config_map = k8s_client.V1ConfigMap(
                metadata=k8s_client.V1ObjectMeta(name=name, namespace=namespace),
                data={key: value},
            )
            v1.create_namespaced_config_map(namespace, body=config_map)
            logger.trace("Created configmap with key", name=name, key=key, value=value)
        else:
            raise e
