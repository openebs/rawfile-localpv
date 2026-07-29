from enum import StrEnum

from .base import FileSystem as FileSystemBase
from .btrfs import BTRFS
from .ext4 import EXT4
from .xfs import XFS


class FileSystemName(StrEnum):
    XFS = "xfs"
    EXT4 = "ext4"
    BTRFS = "btrfs"


filesystems: dict[FileSystemName | None, type[FileSystemBase]] = {
    FileSystemName.XFS: XFS,
    FileSystemName.EXT4: EXT4,
    FileSystemName.BTRFS: BTRFS,
}
