import os
import importlib.metadata

PROVISIONER_NAME = os.getenv("PROVISIONER_NAME", "rawfile.csi.openebs.io")
PROVISIONER_VERSION = os.getenv("PROVISIONER_VERSION") or importlib.metadata.version(
    "rawfile"
)
DATA_DIR = "/data"
D_PERMS = 0o700
F_PERMS = 0o600
OWNER_UMASK = 0o077
RESOURCE_EXHAUSTED_EXIT_CODE = 101
VOLUME_IN_USE_EXIT_CODE = 102
VOLUME_IS_ATTACHED = "openebs.io/rawfile/is-attached"
FORMAT_OPTIONS_KEY = "openebs.io/rawfile/format-options"
CSI_K8S_PVC_NAME_KEY = "csi.storage.k8s.io/pvc/name"
GA_ID = "Ry1UWkdQNDY2MThX"
GA_KEY = "OTFKR2RUZzlRd0duN1ktdnZ1TTR6QQ=="
