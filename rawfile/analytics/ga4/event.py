import humanize
from consts import PROVISIONER_VERSION

from .version_set import VersionSet


class OpenEBSEventBuilder:
    def __init__(self):
        """
        Initialize the builder with default parameters.
        """
        self.params = {}
        self.project("OpenEBS").engine_name("rawfile-localpv").engine_version(
            f"rawfile-v{PROVISIONER_VERSION}"
        )

    def project(self, value: str):
        """
        Specify project name, e.g., "OpenEBS".
        """
        self.params["project"] = value
        return self

    def k8s_version(self, value: str):
        """
        Set Kubernetes version, e.g., "v1.25.15".
        """
        self.params["k8s_version"] = value
        return self

    def engine_name(self, value: str):
        """
        Set name of the engine, e.g., "lvm-localpv".
        """
        self.params["engine_name"] = value
        return self

    def engine_version(self, value: str):
        """
        Set version of the engine, e.g., "lvm-v1.3.0-e927123:11-08-2023-e927123".
        """
        self.params["engine_version"] = value
        return self

    def k8s_default_ns_uid(self, value: str):
        """
        Set UID of the default Kubernetes namespace, e.g., "f5d2a546-19ce-407d-99d4-0655d67e2f76".
        """
        self.params["k8s_default_ns_uid"] = value
        return self

    def engine_installer(self, value: str):
        """
        Set installer of the app, e.g., "lvm-localpv-helm".
        """
        self.params["engine_installer"] = value
        return self

    def node_os(self, value: str):
        """
        Set operating system of the node, e.g., "Ubuntu 20.04.6 LTS".
        """
        self.params["node_os"] = value
        return self

    def node_kernel_version(self, value: str):
        """
        Set kernel version of the node, e.g., "5.4.0-165-generic".
        """
        self.params["node_kernel_version"] = value
        return self

    def node_arch(self, value: str):
        """
        Set architecture of the node, e.g., "linux/amd64".
        """
        self.params["node_arch"] = value
        return self

    def volume_name(self, value: str):
        """
        Set name of the persistent volume object, e.g., "pvc-b3968e30-9020-4011-943a-7ab338d5f19f".
        """
        self.params["vol_name"] = value
        return self

    def volume_claim_name(self, value: str):
        """
        Set name of the persistent volume claim, e.g., "openebs-lvmpv".
        """
        if len(value) > 0:
            self.params["vol_claim_name"] = value
        return self

    def category(self, value: str):
        """
        Set category of the event, e.g., "install", "volume-provision".
        """
        self.params["event_category"] = value
        return self

    def node_count(self, value: int):
        """
        Set number of Kubernetes nodes in the cluster.
        """
        self.params["node_count"] = value
        return self

    def volume_capacity(self, value: int):
        """
        Set size of the volume with no decimal points, rounded up.
        """
        self.params["vol_capacity"] = humanize.naturalsize(
            value, binary=True, format="%.0f"
        )
        return self

    def replica_count(self, value):
        """
        Set number of replicas attached to a volume.
        """
        self.params["vol_replica_count"] = value
        return self

    def build(self):
        """
        Return the built parameters as a dictionary.
        """
        return self.params

    def refresh_version(self, version_set: VersionSet):
        """
        Update builder with values from a VersionSet instance.
        """
        return (
            self.k8s_version(version_set.k8s_version)
            .k8s_default_ns_uid(version_set.uid)
            .engine_installer(version_set.installer_type)
            .node_os(version_set.node_os)
            .node_kernel_version(version_set.node_kernel_version)
            .node_arch(version_set.platform)
            .node_count(version_set.node_count)
        )

    def refresh(self, nodeid):
        """
        Create a VersionSet from a node ID and update builder values.
        """
        version_set = VersionSet(nodeid)
        return self.refresh_version(version_set)
