from consts import PROVISIONER_VERSION
from orchestrator.k8s import namespace_uid, node_count, read_node_info, version_code


class VersionSet:
    def __init__(self, nodeid: str):
        self.id = nodeid
        self.k8s_version = None
        self.uid = None
        self.installer_type = "rawfile-localpv-helm"
        self.node_os = None
        self.node_kernel_version = None
        self.openebs_version = PROVISIONER_VERSION
        self.platform = None
        self.node_count = None
        self.refresh()

    def refresh(self):
        version_info = version_code()
        info = read_node_info(self.id)

        self.k8s_version = version_info["gitVersion"]
        self.uid = namespace_uid("default")
        self.node_os = info.osImage
        self.node_kernel_version = info.kernelVersion
        self.platform = f"{info.operatingSystem}/{info.architecture}"
        self.node_count = node_count()
