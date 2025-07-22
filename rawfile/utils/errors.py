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
