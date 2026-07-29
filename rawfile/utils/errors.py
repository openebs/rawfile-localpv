class UnknownDeviceForMountpointError(ValueError):
    """
    Exception raised when we where unable to find the device for given mountpoint.
    """

    def __init__(self, mountpoint: str):
        self.mountpoint = mountpoint
        self.message = (
            f"Unable to determine the device for mountpoint '{self.mountpoint}'"
        )
        super().__init__(self.message)


class InvalidDeviceForMountpointError(ValueError):
    """
    Exception raised when device that is connected to mountpoint is not a correct device
    """

    def __init__(self, device: str, mountpoint: str):
        self.device = device
        self.mountpoint = mountpoint
        self.message = (
            f"Device {self.device} is not valid for mountpoint {self.mountpoint}"
        )
        super().__init__(self.message)


class SnapshotCreateVolumeInUse(Exception):
    """
    Exception raised when Snapshot is creating and volume is in use
    """

    def __init__(self, volume_id, snapshot_name):
        self.snapshot_name = snapshot_name
        self.volume_id = volume_id
        self.message = f"Unable to create snapshot for used volume, Volume '{self.volume_id}' and Snapshot '{self.snapshot_name}'"
        super().__init__(self.message)


class VolumeCloningNotSupported(NotImplementedError):
    """
    Exception raised when volume create requested cloning another volume
    """

    def __init__(self):
        self.message = "Volume Cloning is not supported"
        super().__init__(self.message)


class FsFreezeNotSupportedOnBlockVolumes(NotImplementedError):
    """
    Exception raised when fsfreeze is requested on block volume
    """

    def __init__(self):
        self.message = "FsFreeze is not supported on block volumes"
        super().__init__(self.message)


class SourceTypeRequired(ValueError):
    """
    Exception raised when source id for create volume is provided but source type is not provided
    """

    def __init__(self, source_id: str):
        self.source_id = source_id
        self.message = f"No Source Type has been provided for {self.source_id}"
        super().__init__(self.message)


class VolumeInUseError(Exception):
    """
    Exception raised when Volume is attached while doing some operations (e.g. delete)
    """

    def __init__(self, volume_id: str):
        self.volume_id = volume_id
        self.message = f"Volume {volume_id} is attached"
        super().__init__(self.message)


class VolumeSourceIsNotReady(Exception):
    """
    Exception raised when Volume is attached while doing some operations (e.g. delete)
    """

    def __init__(self, volume_id, source_volume_id, snapshot_name):
        self.volume_id = volume_id
        self.source_volume_id = source_volume_id
        self.snapshot_name = snapshot_name
        self.message = f"VolumeSource {self.source_volume_id}/{self.snapshot_name} is not ready for destination {self.volume_id}"
        super().__init__(self.message)


class VolumeNotReadyError(Exception):
    """
    Exception raised when Volume is not ready
    """

    def __init__(self, volume_id):
        self.volume_id = volume_id
        self.message = f"Volume {self.volume_id} is not ready"
        super().__init__(self.message)


class DriverConfigNotAvailable(Exception):
    """
    Exception raised when driver config is not available
    """

    def __init__(self):
        self.message = "Driver config is not available, Should run from csi driver"
        super().__init__(self.message)


class NodeDaemonSetNotDefined(Exception):
    """
    Exception raised when node daemonset is not defined
    """

    def __init__(self):
        self.message = "Node Daemonset is not defined"
        super().__init__(self.message)


class UnsupportedAccessTypeError(Exception):
    """
    Exception raised when access type is not supported
    """

    def __init__(self, access_type):
        self.access_type = access_type
        self.message = f"Access type {self.access_type} is not supported"
        super().__init__(self.message)


class LoopDeviceAttachError(Exception):
    """Raised when attaching a loop device for a file fails after repeated attempts."""

    def __init__(self, file, max_attempts, last_exception=None):
        self.file = file
        self.max_attempts = max_attempts
        self.last_exception = last_exception

        if last_exception:
            message = f"Failed to attach loop device for {file} after {max_attempts} attempts: {last_exception}"
        else:
            message = (
                f"Failed to attach loop device for {file} after {max_attempts} attempts"
            )

        super().__init__(message)


class UnknownFileTypeError(Exception):
    """Raised when a filesystem path exists but is neither a file, symlink, nor directory."""

    def __init__(self, path):
        self.path = path
        super().__init__(f"Unknown file type: {path}")
