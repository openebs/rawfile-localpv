from tempfile import TemporaryDirectory

from utils.commands import run

from .base import (
    FileSystem as FileSystemBase,
)
from .base import (
    FileSystemDeleteSnapshotError,
    FileSystemFormatError,
    FileSystemResizeError,
)
from .utils import get_device_for_mountpoint


class BTRFS(FileSystemBase):
    @property
    def __filesystem__(self) -> str:
        return "btrfs"

    def delete_snapshot(self, name: str):
        try:
            with TemporaryDirectory(
                prefix=f"rawfile.{self.__filesystem__}.fs-snapshot."
            ) as tmp_dir:
                try:
                    snapshots_dir = f"{tmp_dir}/.snapshots"
                    snapshot_subvol = f"{snapshots_dir}/{name}"
                    run(
                        f"""
                        set -exo pipefail
                        mount -t btrfs -o subvolid=0 {self.device} {tmp_dir}
                        default_subvol_id=$(btrfs subvolume get-default "{tmp_dir}" | awk '{{print $2}}')
                        default_subvol_path=$(btrfs subvolume list -o "{tmp_dir}" | awk -v id=$default_subvol_id '$2 == id {{print $NF}}')
                        default_subvol="{tmp_dir}/$default_subvol_path"
                        if [ -d "{snapshot_subvol}" ] || [ -f "{snapshot_subvol}" ]; then
                          btrfs subvolume delete "{snapshot_subvol}"
                        fi
                        """,
                        check=True,
                        capture_output=True,
                        executable="bash",
                    )
                finally:
                    if get_device_for_mountpoint(tmp_dir):
                        run(
                            f"umount {tmp_dir}",
                            check=True,
                            capture_output=True,
                        )
        except Exception as e:
            raise FileSystemDeleteSnapshotError.from_exc(e, self.__filesystem__)

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
