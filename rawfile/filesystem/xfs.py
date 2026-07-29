import subprocess

from utils.commands import run
from utils.logs import logger

from .base import (
    FileSystem as FileSystemBase,
)
from .base import (
    FileSystemFreezeError,
    FileSystemResizeError,
    FileSystemUnFreezeError,
)


class XFS(FileSystemBase):
    @property
    def __filesystem__(self) -> str:
        return "xfs"

    def resize(self) -> str:
        try:
            output = run(
                f"xfs_growfs -d {self.mountpoint}",
                check=True,
                capture_output=True,
            )
            return output.stdout.decode()
        except Exception as e:
            raise FileSystemResizeError.from_exc(e, self.__filesystem__)

    def freeze(self):
        """
        Freeze the filesystem

        returns the output of the freeze command (optional).
        """
        try:
            return run(
                f"xfs_freeze -f {self.mountpoint}",
                check=True,
                capture_output=True,
            ).stdout.decode()
        except subprocess.CalledProcessError as e:
            if "Device or resource busy" in e.stderr.decode().strip():
                logger.warning(
                    "Filesystem already frozen.",
                    filesystem=self.__filesystem__,
                    mountpoint=self.mountpoint,
                    device=self.device,
                )
                return
            raise FileSystemFreezeError.from_exc(e, self.__filesystem__)
        except Exception as e:
            raise FileSystemFreezeError.from_exc(e, self.__filesystem__)

    def unfreeze(self):
        """
        Unfreeze the filesystem

        returns the output of the unfreeze command (optional).
        """
        try:
            run(
                f"xfs_freeze -u {self.mountpoint}",
                check=True,
                capture_output=True,
            ).stdout.decode()
        except subprocess.CalledProcessError as e:
            if "Invalid argument" in e.stderr.decode().strip():
                logger.warning(
                    "Filesystem is not freezed.",
                    filesystem=self.__filesystem__,
                    mountpoint=self.mountpoint,
                    device=self.device,
                )
                return
        except Exception as e:
            raise FileSystemUnFreezeError.from_exc(e, self.__filesystem__)
