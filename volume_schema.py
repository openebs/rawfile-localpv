import sys

LATEST_SCHEMA_VERSION = 1  # type: int


def migrate_0_to_1(data: dict) -> dict:
    data["schema_version"] = 1
    return data


def migrate_to(data: dict, version: int) -> dict:
    current = data.get("schema_version", 0)
    if current > version:
        raise Exception(
            f"Current schema version ({current}) is newer than target schema version ({version})"
        )
    for i in range(current, version):
        migrate_fn = getattr(sys.modules[__name__], f"migrate_{i}_to_{i + 1}")
        data = migrate_fn(data)
    return data
