from utils.commands import run

from .base import (
    FileSystem as FileSystemBase,
)
from .base import (
    FileSystemResizeError,
)


class EXT4(FileSystemBase):
    @property
    def __filesystem__(self) -> str:
        return "ext4"

    def resize(self) -> str:
        try:
            output = run(
                f"resize2fs {self.device}",
                check=True,
                capture_output=True,
            )
            return output.stdout.decode()
        except Exception as e:
            raise FileSystemResizeError.from_exc(e, self.__filesystem__)
