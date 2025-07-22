from abc import ABC, ABCMeta, abstractmethod
import subprocess
from .utils import get_device_for_mountpoint, get_device_fs
from pathlib import Path
from typing import Self
from utils.commands import run
from utils.errors import InvalidDeviceForMountpointError


class NotSupportedError(NotImplementedError):
    """
    Exception raised when a feature is not supported by the current filesystem.
    """

    def __init__(self, feature: str) -> None:
        super().__init__(
            f"Feature '{feature}' is not supported by the current filesystem."
        )


class FileSystemOperationError(Exception):
    """
    Exception raised when a filesystem operation has been failed.
    """

    operation: str = ""

    def __init__(self, filesystem: str, message: str) -> None:
        self.filesystem = filesystem
        self.message = f"Operation '{self.operation}' failed on filesystem '{self.filesystem}': {message}"
        super().__init__(self.message)

    @classmethod
    def from_exc(cls, exc: Exception, filesystem: str) -> Self:
        msg = str(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            msg = exc.stderr.decode()
        return cls(filesystem=filesystem, message=msg)


class FileSystemFormatError(FileSystemOperationError):
    """
    Exception raised when filesystem format has been failed.
    """

    operation: str = "format"


class FileSystemMountError(FileSystemOperationError):
    """
    Exception raised when filesystem mount has been failed.
    """

    operation = "mount"


class FileSystemUnmountError(FileSystemOperationError):
    """
    Exception raised when filesystem unmount has been failed.
    """

    operation = "unmount"


class FileSystemResizeError(FileSystemOperationError):
    """
    Exception raised when filesystem resize has been failed.
    """

    operation = "resize"


class FileSystemCreateSnapshotError(FileSystemOperationError):
    """
    Exception raised when filesystem resize has been failed.
    """

    operation = "create snapshot"


class FileSystemDeleteSnapshotError(FileSystemOperationError):
    """
    Exception raised when filesystem resize has been failed.
    """

    operation = "delete snapshot"


class UnknownFileSystemError(ValueError):
    """
    Exception raised when we where unable to find the filesystem for given device.
    """

    def __init__(self, device: str, volume_id: str | None = None):
        self.device = device
        self.volume_id = volume_id
        self.message = f"Unable to determine the filesystem for device '{self.device}' {f" and volume id '{self.volume_id}'" if self.volume_id else ''}, Is the volume initialized?"
        super().__init__(self.message)


class DeviceIsNotBlockError(ValueError):
    """
    Exception raised when input device is not a blockdev.
    """

    def __init__(self, device: str):
        self.device = device
        self.message = f"'{device}' Is not a block device"
        super().__init__(self.message)


class InvalidMountpointError(ValueError):
    """
    Exception raised when mountpoint is not provided correctly.
    """

    def __init__(self):
        self.message = "Mountpoint parameter is not set correctly"
        super().__init__(self.message)


class FileSystem(ABC, metaclass=ABCMeta):
    def __init__(self, device: str, mountpoint: str | None = None):
        """
        Initialize the file system with the given device.
        """
        if not Path(device).is_block_device():
            raise DeviceIsNotBlockError(device=device)
        self.device = Path(device).resolve().as_posix()
        self.mountpoint = mountpoint

    @property
    @abstractmethod
    def __filesystem__(self) -> str:
        """
        The name of the filesystem.
        """
        raise NotImplementedError("Filesystem name not defined")

    @classmethod
    def __subclasshook__(cls, subclass):
        """
        Check if the subclass implements the required methods.
        """
        required_features = [
            "resize",
        ]
        for method in required_features:
            if not (hasattr(subclass, method) and callable(getattr(subclass, method))):
                return False
        return True

    def create_snapshot(self, name: str):
        """
        Create a snapshot of the current state of the file system.
        """
        raise NotSupportedError("create_snapshot")

    def delete_snapshot(self, name: str):
        """
        Delete the selected snapshot of the file system.
        """
        raise NotSupportedError("delete_snapshot")

    def restore_snapshot(self, name: str):
        # FIXME: We will probably have some other parameters
        """
        Delete the selected snapshot of the file system.
        """
        raise NotSupportedError("restore_snapshot")

    def format_fs(self, options: list[str] = []) -> str | None:
        """
        Format the file system.

        returns the output of the format command (optional).
        """
        try:
            output = run(
                f"mkfs.{self.__filesystem__} {' '.join(options)} {self.device}",
                check=True,
                capture_output=True,
            )
            return output.stdout.decode()
        except Exception as e:
            raise FileSystemFormatError.from_exc(e, self.__filesystem__)

    def mount(
        self, mountpoint: str | None = None, options: list[str] = []
    ) -> str | None:
        """
        Mount the file system.
        mountpoint should default to self.mountpoint and
        raise error if we have not found any
        Should also do
            self.mountpoint = mountpoint

        returns the output of the mount command (optional).
        """
        if mountpoint is None:
            if self.mountpoint is None:
                raise InvalidMountpointError()
            mountpoint = self.mountpoint
        self.mountpoint = mountpoint
        current_dev = get_device_for_mountpoint(mountpoint)
        if current_dev == self.device:
            return f"Device {self.device} already mounted at {mountpoint}"
        elif current_dev:
            raise InvalidDeviceForMountpointError(
                device=self.device, mountpoint=mountpoint
            )
        try:
            Path(mountpoint).mkdir(exist_ok=True)
            opt_str = f"-o {','.join(options)} " if len(options) else ""
            output = run(
                f"mount -t {self.__filesystem__} {opt_str}{self.device} {mountpoint}",
                check=True,
                capture_output=True,
            )
            return output.stdout.decode()
        except Exception as e:
            raise FileSystemMountError.from_exc(e, self.__filesystem__)

    def unmount(self, clear_mountpoint=False) -> str | None:
        """
        Unmount the file system.

        returns the output of the unmount command (optional).
        """
        output = None
        if not self.mountpoint:
            raise InvalidMountpointError()
        current_dev = get_device_for_mountpoint(self.mountpoint)
        if current_dev and current_dev != self.device:
            raise InvalidDeviceForMountpointError(
                device=current_dev, mountpoint=self.mountpoint
            )
        try:
            # NOTE: this is due to if we crashed/restarted during/after unmount
            # e.g we have unmounted, but not cleared the mountpoint
            if current_dev:
                _output = run(
                    f"umount {self.mountpoint}",
                    check=True,
                    capture_output=True,
                )
                output = _output.stdout.decode()
            if clear_mountpoint:
                # NOTE: using rmdir since unmounted path should be empty
                Path(self.mountpoint).rmdir()
        except Exception as e:
            raise FileSystemUnmountError.from_exc(e, self.__filesystem__)
        return output

    @abstractmethod
    def resize(self) -> str | None:
        """
        Resize the file system.
        This should be run after the partition has been resized.

        returns the output of the resize command (optional).
        """
        raise NotSupportedError("resize")

    def format_and_mount(
        self,
        mountpoint: str | None = None,
        mount_options: list[str] = [],
        format_options: list[str] = [],
    ):
        if not get_device_fs(self.device):
            self.format_fs(format_options)

        self.mount(mountpoint, mount_options)
