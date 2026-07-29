import sys
from typing import Final

LATEST_SCHEMA_VERSION: Final[int] = 7


def migrate_0_to_1(data: dict) -> dict:
    data["schema_version"] = 1
    return data


def migrate_1_to_2(data: dict) -> dict:
    data["schema_version"] = 2
    data.setdefault("fs_type", "ext4")
    return data


def migrate_2_to_3(data: dict) -> dict:
    data["schema_version"] = 3
    deleted_at = data.get("deleted_at", None)
    if deleted_at is not None:
        gc_at = deleted_at + 7 * 24 * 60 * 60
        data["gc_at"] = gc_at
    return data


def migrate_3_to_4(data: dict) -> dict:
    data["schema_version"] = 4
    data["thin_provision"] = True
    return data


def migrate_4_to_5(data: dict) -> dict:
    data["schema_version"] = 5
    data["ready"] = True
    return data


def migrate_5_to_6(data: dict) -> dict:
    from config import config

    data["schema_version"] = 6
    data["storage_pool"] = config.csi_driver.default_pool
    return data


def migrate_6_to_7(data: dict) -> dict:
    data["schema_version"] = 7
    data.pop("reflink_attached", None)
    return data


class SchemaVersionTooNewError(Exception):
    """Raised when the current schema version is newer than the target schema version."""

    def __init__(self, current, target):
        self.current = current
        self.target = target
        super().__init__(
            f"Current schema version ({current}) is newer than target schema version ({target})"
        )


def migrate_to(data: dict, version: int) -> dict:
    current = data.get("schema_version", 0)
    if current > version:
        raise SchemaVersionTooNewError(current=current, target=version)
    for i in range(current, version):
        migrate_fn = getattr(sys.modules[__name__], f"migrate_{i}_to_{i + 1}")
        data = migrate_fn(data)
    return data
