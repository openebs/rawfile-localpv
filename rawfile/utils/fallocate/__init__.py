try:
    import _fallocate
except ImportError:
    from .build import ffi

    ffi.compile()
    import _fallocate


class FallocateFailed(Exception):
    def __init__(self, returncode):
        self.returncode = returncode
        self.message = f"Fallocate failed, Return code: {self.returncode}"
        super().__init__(self.message)


def fallocate(fd, mode, offset, length):
    if _fallocate.lib.fallocate(fd, mode, offset, length) != 0:
        raise FallocateFailed()
