import os

PROVISIONER_NAME = os.getenv("PROVISIONER_NAME", "rawfile.csi.openebs.io")
PROVISIONER_VERSION = "0.8.0"
DATA_DIR = "/data"
CONFIG = {}
RESOURCE_EXHAUSTED_EXIT_CODE = 101
VOLUME_IN_USE_EXIT_CODE = 102
