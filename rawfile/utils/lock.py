import fcntl

from utils.rawfile import lock_file

"""
  This can be used to ensure there's only 1 operation running at a time for a given volume.
"""


class VolLock:
    def __init__(self, volume_id, clear_on_release: bool = True, wait: bool = False):
        self.path = lock_file(volume_id)
        self.path.touch(exist_ok=True)
        self.file = open(self.path, "a")  # noqa: SIM115  ## We have our own context management
        self.clear_on_release = clear_on_release
        self.wait = wait

    def __enter__(self):
        while True:
            try:
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError:
                if self.wait:
                    continue
                raise

    def release(self):
        if hasattr(self, "file"):
            fcntl.flock(self.file, fcntl.LOCK_UN)
            self.file.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        if self.clear_on_release:
            self.path.unlink(missing_ok=True)
