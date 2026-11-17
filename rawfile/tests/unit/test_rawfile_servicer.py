from types import SimpleNamespace

import pytest
from config import config
from csi import csi_pb2
from rawfile_servicer import RawFileControllerServicer, RawFileNodeServicer


@pytest.fixture(autouse=True)
def capabilities(monkeypatch):
    monkeypatch.setattr(
        config,
        "csi_driver",
        SimpleNamespace(
            capabilities=SimpleNamespace(
                snapshots=SimpleNamespace(enabled=False),
                resize=SimpleNamespace(enabled=False),
            )
        ),
    )


def test_controller_supports_single_node_multi_writer():
    Cap = csi_pb2.ControllerServiceCapability
    servicer = RawFileControllerServicer(task_manager=None)

    response = servicer.ControllerGetCapabilities(
        csi_pb2.ControllerGetCapabilitiesRequest(), None
    )

    assert Cap(rpc=Cap.RPC(type=Cap.RPC.SINGLE_NODE_MULTI_WRITER)) in (
        response.capabilities
    )


def test_node_supports_single_node_multi_writer():
    Cap = csi_pb2.NodeServiceCapability
    servicer = RawFileNodeServicer(node_name="node-1")

    response = servicer.NodeGetCapabilities(csi_pb2.NodeGetCapabilitiesRequest(), None)

    assert Cap(rpc=Cap.RPC(type=Cap.RPC.SINGLE_NODE_MULTI_WRITER)) in (
        response.capabilities
    )
