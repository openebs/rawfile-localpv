from tempfile import TemporaryDirectory

from utils.commands import run

from .base import (
    FileSystem as FileSystemBase,
)
from .base import (
    FileSystemFormatError,
    FileSystemResizeError,
)
from .utils import get_device_for_mountpoint


class BTRFS(FileSystemBase):
    @property
    def __filesystem__(self) -> str:
        return "btrfs"

    def format_fs(self, options: list[str] | None = None):
        with TemporaryDirectory(
            prefix=f"rawfile.{self.__filesystem__}.fs-bootstrap."
        ) as tmp_dir:
            try:
                default_subvol = f"{tmp_dir}/default"
                output = run(
                    f"""
                    set -exo pipefail
                    mkfs.{self.__filesystem__} {" ".join(options or [])} {self.device}
                    mount -t btrfs {self.device} {tmp_dir}
                    btrfs subvolume create {default_subvol}
                    btrfs subvolume set-default {default_subvol}
                    """,
                    check=True,
                    capture_output=True,
                    executable="bash",
                )
            except Exception as e:
                raise FileSystemFormatError.from_exc(e, self.__filesystem__)
            finally:
                if get_device_for_mountpoint(tmp_dir):
                    run(
                        f"umount {tmp_dir}",
                        check=True,
                        capture_output=True,
                    )

            return output.stdout.decode()

    def resize(self) -> str:
        try:
            output = run(
                f"btrfs filesystem resize max {self.mountpoint}",
                check=True,
                capture_output=True,
            )
            return output.stdout.decode()
        except Exception as e:
            raise FileSystemResizeError.from_exc(e, self.__filesystem__)
