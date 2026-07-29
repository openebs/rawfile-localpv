import json
import logging
from shutil import which

import common

logger = logging.getLogger(__name__)

helm_bin = which("helm")


class HelmReleaseClient:
    def __init__(self):
        self.namespace = "openebs"
        self.release = "rawfile-localpv"

    def get_metadata(self):
        args = [
            "get",
            "metadata",
            self.release,
            "-n",
            self.namespace,
            "-o",
            "json",
        ]
        return json.loads(common.run(helm_bin, args, log_run=False))

    def get_deployed(self):
        args = [
            "ls",
            "-n",
            self.namespace,
            "--deployed",
            f"--filter=^{self.release}$",
            "-o=json",
        ]
        return common.run(helm_bin, args)

    def install_rawfile(self):
        output_json = json.loads(self.get_deployed())
        if len(output_json) == 1:
            current_version = output_json[0]["app_version"]

            logger.warning(
                f"Helm release '{self.release}' already exists in the '{self.namespace}' namespace @ v{current_version}."
            )
            return

        logger.info(f"Installing {self.release} helm chart from local directory")
        common.run(f"{common.root_dir()}/.ci/e2e-test/setup.sh")
