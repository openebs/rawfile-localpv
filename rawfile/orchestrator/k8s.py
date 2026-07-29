import functools
import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from time import sleep

from config import config
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes import watch
from kubernetes.client.rest import ApiException
from utils.errors import NodeDaemonSetNotDefined
from utils.logs import logger


class NodeUnavailableError(Exception):
    def __init__(self, node_name):
        self.node_name = node_name
        super().__init__(f"Node {self.node_name} is not available")


__config_loaded = False


def load_config(func):
    @functools.wraps(func)
    def wrap(*args, **kwargs):
        global __config_loaded
        if not __config_loaded:
            if os.getenv("KUBERNETES_SERVICE_HOST"):
                k8s_config.load_incluster_config()
            else:
                k8s_config.load_config()
            __config_loaded = True
        return func(*args, **kwargs)

    return wrap


class K8sEventType(StrEnum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    BOOKMARK = "BOOKMARK"
    ERROR = "ERROR"


@load_config
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
    start = datetime.now(UTC)
    while not pred():
        sleep(0.5)
    end = datetime.now(UTC)
    logger.info(
        f"Finished waiting for {desc}", start=start, end=end, latency=end - start
    )


@load_config
def namespace_uid(namespace: str) -> str:
    v1 = k8s_client.CoreV1Api()
    namespace = v1.read_namespace(name=namespace)
    return namespace.metadata.uid


@load_config
def version_code():
    version_api = k8s_client.VersionApi()
    return version_api.get_code()


@load_config
def read_node_info(nodeid):
    v1 = k8s_client.CoreV1Api()
    node = v1.read_node(name=nodeid)
    info = node.status.node_info
    return info


@load_config
def node_count() -> int:
    v1 = k8s_client.CoreV1Api()
    node_count = len(v1.list_node().items)
    return node_count


@load_config
def read_config_map(name: str):
    v1 = k8s_client.CoreV1Api()
    try:
        config_map = v1.read_namespaced_config_map(name, namespace=config.namespace)
        return config_map.data or {}
    except ApiException as e:
        if e.status == 404:
            return {}
        raise


@load_config
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
            raise


class NodeIPMapping:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None

    @load_config
    def start(self):
        if not config.node_ds:
            raise NodeDaemonSetNotDefined()
        self.apps_v1 = k8s_client.AppsV1Api()
        self.core_v1 = k8s_client.CoreV1Api()
        ds = self.apps_v1.read_namespaced_daemon_set(
            namespace=config.namespace, name=config.node_ds
        )
        self.selector = ds.spec.selector.match_labels
        self.label_selector = ",".join(f"{k}={v}" for k, v in self.selector.items())

        self._mapping = {}
        self.reload_mapping()
        self._thread = threading.Thread(target=self.watch_daemonset_pods, daemon=True)
        self._thread.start()

    def reload_mapping(self):
        pods = self.core_v1.list_namespaced_pod(
            namespace=config.namespace, label_selector=self.label_selector
        )
        mapping = {}
        for pod in pods.items:
            if pod.status.phase == "Running" and pod.status.pod_ip:
                mapping[pod.spec.node_name] = pod.status.pod_ip
        self._mapping = mapping

    def get_all_nodes(self):
        return self._mapping

    def get_node_ip(self, node_name):
        ip = self._mapping.get(node_name, None)
        if not ip:
            raise NodeUnavailableError(node_name)
        return ip

    def _reload_and_raise(self, exc: Exception):
        self.reload_mapping()
        raise exc

    def watch_daemonset_pods(self):
        w = watch.Watch()
        while not self._stop_event.is_set():
            retrying = False
            try:
                for event in w.stream(
                    self.core_v1.list_namespaced_pod,
                    namespace=config.namespace,
                    label_selector=self.label_selector,
                    timeout_seconds=60,  # give it a heartbeat
                ):
                    if self._stop_event.is_set():
                        w.stop()
                        break
                    actions: dict[K8sEventType, Callable] = {
                        K8sEventType.DELETED: lambda event=event: self._mapping.pop(
                            event["object"].spec.node_name
                        ),
                        K8sEventType.ADDED: lambda event=event: (
                            self._mapping.__setitem__(
                                event["object"].spec.node_name,
                                event["object"].status.pod_ip,
                            )
                        ),
                        K8sEventType.MODIFIED: lambda event=event: (
                            self._mapping.__setitem__(
                                event["object"].spec.node_name,
                                event["object"].status.pod_ip,
                            )
                        ),
                        K8sEventType.ERROR: lambda: self._reload_and_raise(
                            Exception("Got Error Event on wather")
                        ),
                        K8sEventType.BOOKMARK: lambda: None,
                    }
                    actions[event["type"]]()
                    retrying = False
            except Exception:
                if not retrying:
                    logger.exception("DS Watcher Error, retrying...")
                retrying = True

    def stop(self):
        if self._thread:
            self._stop_event.set()
            self._thread.join(timeout=2)


node_ip_mapping = NodeIPMapping()
