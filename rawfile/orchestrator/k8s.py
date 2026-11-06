import functools
import threading
from datetime import UTC, datetime
from enum import StrEnum
from time import sleep

import msgspec
from config import config
from lightkube import ApiError, Client, KubeConfig
from lightkube.models.core_v1 import (
    NodeSelector,
    NodeSelectorRequirement,
    NodeSelectorTerm,
    VolumeNodeAffinity,
)
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.apps_v1 import DaemonSet
from lightkube.resources.core_v1 import (
    ConfigMap,
    Namespace,
    Node,
    PersistentVolume,
    Pod,
)
from utils.errors import NodeDaemonSetNotDefined
from utils.logs import logger
from utils.remote import prune_stale_stubs


class NodeUnavailableError(Exception):
    def __init__(self, node_name):
        self.node_name = node_name
        super().__init__(f"Node {self.node_name} is not available")


@functools.cache
def k8s() -> Client:
    # in-cluster service account, else KUBECONFIG / ~/.kube/config
    kube_config = KubeConfig.from_env().get()
    if config.tls_insecure_skip_verify:
        kube_config = kube_config._replace(
            cluster=msgspec.structs.replace(kube_config.cluster, insecure=True)
        )
    return Client(kube_config)


class K8sEventType(StrEnum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    BOOKMARK = "BOOKMARK"
    ERROR = "ERROR"


def volume_to_node(volume_id):
    pv = k8s().get(PersistentVolume, volume_id)
    curr_node_affinity = pv.spec.nodeAffinity
    node_name = (
        curr_node_affinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0]
    )
    expected_affinity = VolumeNodeAffinity(
        required=NodeSelector(
            nodeSelectorTerms=[
                NodeSelectorTerm(
                    matchExpressions=[
                        NodeSelectorRequirement(
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


def namespace_uid(namespace: str) -> str:
    return k8s().get(Namespace, namespace).metadata.uid


def version_code() -> dict:
    # lightkube has no wrapper for /version; use its (authenticated) httpx client
    response = k8s()._client._client.get("/version")
    response.raise_for_status()
    return response.json()


def read_node_info(nodeid):
    return k8s().get(Node, nodeid).status.nodeInfo


def node_count() -> int:
    return sum(1 for _ in k8s().list(Node))


def read_config_map(name: str):
    try:
        config_map = k8s().get(ConfigMap, name, namespace=config.namespace)
        return config_map.data or {}
    except ApiError as e:
        if e.status.code == 404:
            return {}
        raise


def write_config_map(name: str, key: str, value: str, overwrite=False):
    namespace = config.namespace

    try:
        config_map = k8s().get(ConfigMap, name, namespace=namespace)
        data = config_map.data or {}

        if key not in data:
            data[key] = value
            config_map.data = data
            k8s().replace(config_map)
            logger.trace("Added key", name=name, key=key, value=value)
        elif overwrite:
            data[key] = value
            config_map.data = data
            k8s().replace(config_map)
            logger.trace("Modified key", name=name, key=key, value=value, old=data[key])
        else:
            logger.trace(
                "Not modifying existing key",
                name=name,
                key=key,
                value=value,
                old=data[key],
            )

    except ApiError as e:
        if e.status.code == 404:
            logger.trace("Creating new configmap", name=name, key=key, value=value)
            config_map = ConfigMap(
                metadata=ObjectMeta(name=name, namespace=namespace),
                data={key: value},
            )
            k8s().create(config_map)
            logger.trace("Created configmap with key", name=name, key=key, value=value)
        else:
            raise


class NodeIPMapping:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if not config.node_ds:
            raise NodeDaemonSetNotDefined()
        ds = k8s().get(DaemonSet, config.node_ds, namespace=config.namespace)
        self.selector = ds.spec.selector.matchLabels

        # pod name -> (node name, pod ip), for the running pods with an ip
        self._pods: dict[str, tuple[str, str]] = {}
        self._mapping: dict[str, str] = {}
        resource_version = self.reload_mapping()
        self._thread = threading.Thread(
            target=self.watch_daemonset_pods, args=(resource_version,), daemon=True
        )
        self._thread.start()

    def reload_mapping(self) -> str:
        """Rebuild the mapping from a fresh list, returning its resourceVersion."""
        pods = k8s().list(Pod, namespace=config.namespace, labels=self.selector)
        self._pods = {}
        for pod in pods:
            self._track(K8sEventType.ADDED, pod)
        self._publish()
        return pods.resourceVersion

    def _track(self, op: str, pod: Pod):
        name = pod.metadata.name
        node = pod.spec.nodeName if pod.spec else None
        ip = pod.status.podIP if pod.status else None
        running = pod.status is not None and pod.status.phase == "Running"
        if op != K8sEventType.DELETED and running and node and ip:
            self._pods[name] = (node, ip)
        else:
            self._pods.pop(name, None)

    def _publish(self):
        # Replace (rather than mutate) the dict so readers on other threads
        # never iterate over it while it changes. During a rolling update the
        # newer pod on a node wins, and deleting the old one cannot drop it.
        self._mapping = {node: ip for node, ip in self._pods.values()}

    def get_all_nodes(self):
        return self._mapping

    def get_node_ip(self, node_name):
        ip = self._mapping.get(node_name, None)
        if not ip:
            raise NodeUnavailableError(node_name)
        return ip

    def watch_daemonset_pods(self, resource_version: str | None = None):
        backoff = 1
        while not self._stop_event.is_set():
            try:
                if resource_version is None:
                    # (re)list so pods deleted while we weren't watching are dropped
                    resource_version = self.reload_mapping()
                # Watch from the listed version: no replayed ADDED events, no gap.
                # lightkube reconnects every server_timeout from the last seen
                # version; errors (incl. ERROR events, e.g. 410 Gone) are raised.
                for op, pod in k8s().watch(
                    Pod,
                    namespace=config.namespace,
                    labels=self.selector,
                    server_timeout=60,
                    resource_version=resource_version,
                ):
                    if self._stop_event.is_set():
                        return
                    if op == K8sEventType.BOOKMARK:
                        continue
                    self._track(op, pod)
                    self._publish()
                    prune_stale_stubs(self._mapping.values())
                    backoff = 1
            except Exception as e:
                resource_version = None
                if isinstance(e, ApiError) and e.status.code == 410:
                    # the watched resourceVersion expired: routine, just relist
                    logger.info("DS watch expired, relisting")
                    continue
                logger.exception("DS Watcher Error, relisting", backoff=backoff)
                self._stop_event.wait(backoff)
                backoff = min(backoff * 2, 30)

    def stop(self):
        if self._thread:
            self._stop_event.set()
            self._thread.join(timeout=2)


node_ip_mapping = NodeIPMapping()
