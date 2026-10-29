import json
from datetime import timedelta
from pathlib import Path

import pytest
from utils.logs import _json_serialize, logger


@pytest.fixture
def records():
    records = []
    handler = logger.add(records.append, format="{message}")
    yield records
    logger.remove(handler)


def serialized(records):
    assert len(records) == 1
    return json.loads(_json_serialize(records[0].record))


def test_json_log_serializes_path_fields(records):
    logger.warning(
        "COW test failed",
        source=Path("/var/csi/rawfile"),
        destination=Path("/var/csi/rawfile/pvc-1"),
    )

    out = serialized(records)
    assert out["message"] == "COW test failed"
    assert out["source"] == "/var/csi/rawfile"
    assert out["destination"] == "/var/csi/rawfile/pvc-1"


def test_json_log_serializes_exception_fields(records):
    logger.error(
        "TaskManager Worker encountered an error",
        error=FileNotFoundError(2, "No such file or directory"),
    )

    out = serialized(records)
    assert out["error"] == "[Errno 2] No such file or directory"


def test_json_log_keeps_known_types(records):
    logger.info("done", latency=timedelta(seconds=1), ids=("pvc-1",), size=16)

    out = serialized(records)
    assert out["latency"] == "1s"
    assert out["ids"] == ["pvc-1"]
    assert out["size"] == 16
