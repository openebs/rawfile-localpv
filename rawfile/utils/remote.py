import asyncio
import ipaddress
from threading import Lock

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


_stub_lock = Lock()
_channels: dict[str, grpc.Channel] = {}
_stubs: dict[str, internal_pb2_grpc.InternalStub] = {}

_async_channels: dict[str, grpc.aio.Channel] = {}
_async_stubs: dict[str, internal_pb2_grpc.InternalStub] = {}
_async_channel_loops: dict[str, asyncio.AbstractEventLoop] = {}


def __build_remote_hostport(remote_address: str):
    node_ip = ipaddress.ip_address(remote_address)
    if node_ip.version == 6:
        remote_address = f"[{remote_address}]"
    return f"{remote_address}:{config.internal_port}"


def __extract_remote_hostport(hostport: str) -> tuple[str, int]:
    address, _, port = hostport.rpartition(":")
    if address.startswith("[") and address.endswith("]"):
        address = address[1:-1]
    ipaddress.ip_address(address)
    return address, int(port)


def prune_stale_stubs(node_ips: set[str]) -> None:
    """Evict cached channels/stubs whose node-plugin pod IP no longer exists."""
    with _stub_lock:
        # aio channels: close gracefully on their owning event loop
        for target in list(_async_channels):
            ip, _ = __extract_remote_hostport(target)
            if ip in node_ips:
                continue
            channel = _async_channels.pop(target, None)
            _async_stubs.pop(target, None)
            loop = _async_channel_loops.pop(target, None)
            if channel is None:
                continue
            if loop is not None and not loop.is_closed():
                asyncio.run_coroutine_threadsafe(channel.close(), loop)
            # else: ref-drop is safe — grpc.aio Channel.__del__ closes the core channel

        # sync channels: close() explicitly (also cancels doomed in-flight RPCs)
        for target in list(_channels):
            ip, _ = __extract_remote_hostport(target)
            if ip in node_ips:
                continue
            channel = _channels.pop(target, None)
            _stubs.pop(target, None)
            if channel is not None:
                channel.close()


def get_internal_grpc_stub(
    remote_address: str,
    aio: bool = False,
) -> internal_pb2_grpc.InternalStub:

    target = __build_remote_hostport(remote_address)

    with _stub_lock:
        if aio:
            stub = _async_stubs.get(target)
            if stub is not None:
                return stub

            channel = grpc.aio.insecure_channel(target)
            stub = internal_pb2_grpc.InternalStub(channel)

            _async_channels[target] = channel
            _async_stubs[target] = stub
            try:
                _async_channel_loops[target] = asyncio.get_running_loop()
            except RuntimeError:
                pass  # created outside async context; prune falls back to ref-drop

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
