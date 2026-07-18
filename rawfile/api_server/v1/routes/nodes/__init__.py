import asyncio

from api_server.v1.models import (
    Node,
    NodeList,
    PoolsStat,
    PoolStat,
)
from fastapi import APIRouter, Response, status
from internal import internal_pb2
from orchestrator.k8s import node_ip_mapping
from utils.logs import logger
from utils.remote import get_internal_grpc_stub, internal_auth_metadata

from .tasks import router as tasks_router
from .volumes import router as volumes_router

router = APIRouter()
router.include_router(tasks_router, prefix="/{node_name}/tasks", tags=["tasks"])
router.include_router(
    volumes_router, prefix="/{node_name}/{pool_name}", tags=["volumes"]
)


async def get_node_pool_stat(node_ip):
    stub = get_internal_grpc_stub(node_ip, aio=True)
    return await stub.GetPoolsStats(
        internal_pb2.GetPoolsStatsRequest(),
        metadata=[internal_auth_metadata()],
        timeout=15,
    )


semaphore = asyncio.Semaphore(20)


async def build_node(node_name: str, node_ip: str) -> Node:
    async with semaphore:
        node = Node(name=node_name, ip=node_ip, online=True)  # type: ignore
        try:
            pool_stats = await get_node_pool_stat(node_ip)
            node.pools_stat = PoolsStat(
                {
                    name: PoolStat(
                        reserved_capacity=pool.reserved_capacity,
                        path=pool.path,
                        reserved_capacity_mode=pool.reserved_capacity_mode,
                        capacity=pool.capacity,
                        copy_on_write_supported=pool.copy_on_write_supported,
                    )
                    for name, pool in pool_stats.stats.items()
                },
            )
        except Exception:
            logger.exception(
                "Unable to get Node Information",
                node_ip=node_ip,
                node_name=node_name,
            )
            node.online = False
        return node


@router.get("")
async def get_nodes() -> NodeList:
    node_ips = node_ip_mapping.get_all_nodes()
    tasks = [build_node(node_name, node_ip) for node_name, node_ip in node_ips.items()]
    return [item for item in await asyncio.gather(*tasks)]


@router.get("/{node_name}")
async def get_single_node(node_name: str, response: Response) -> Node:
    ip = node_ip_mapping.get_node_ip(node_name)
    result = await build_node(node_name, ip)
    if not result.online:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return result
