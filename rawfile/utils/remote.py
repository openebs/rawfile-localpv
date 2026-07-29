import ipaddress

import grpc
from config import config
from internal import internal_pb2_grpc
from internal_svc import SIGNATURE_METADATA

import utils.storage_pool


def get_capacity(storage_pool: str | None = None):
    cap = utils.storage_pool.get_capacity(storage_pool)
    return max(0, cap)


def internal_auth_metadata():
    return (SIGNATURE_METADATA, config.internal_signature)


_channels: dict[str, grpc.Channel] = {}
_stubs: dict[str, internal_pb2_grpc.InternalStub] = {}

_async_channels: dict[str, grpc.aio.Channel] = {}
_async_stubs: dict[str, internal_pb2_grpc.InternalStub] = {}


def get_internal_grpc_stub(
    remote_address: str,
    aio: bool = False,
) -> internal_pb2_grpc.InternalStub:
    node_ip = ipaddress.ip_address(remote_address)

    if node_ip.version == 6:
        remote_address = f"[{remote_address}]"

    target = f"{remote_address}:{config.internal_port}"

    if aio:
        stub = _async_stubs.get(target)
        if stub is not None:
            return stub

        channel = grpc.aio.insecure_channel(target)
        stub = internal_pb2_grpc.InternalStub(channel)

        _async_channels[target] = channel
        _async_stubs[target] = stub

        return stub

    stub = _stubs.get(target)
    if stub is not None:
        return stub

    channel = grpc.insecure_channel(target)
    stub = internal_pb2_grpc.InternalStub(channel)

    _channels[target] = channel
    _stubs[target] = stub

    return stub


async def shutdown_grpc_channels():
    for channel in _async_channels.values():
        await channel.close()
    for channel in _channels.values():
        channel.close()
