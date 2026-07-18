from api_server.v1.models import (
    VolumesStat,
    VolumeStat,
)
from fastapi import APIRouter, HTTPException, status
from internal import internal_pb2
from orchestrator.k8s import NodeUnavailableError, node_ip_mapping
from utils.remote import get_internal_grpc_stub, internal_auth_metadata

router = APIRouter()


@router.get("")
async def get_node_pool_volumes(node_name: str, pool_name: str) -> VolumesStat:
    try:
        ip = node_ip_mapping.get_node_ip(node_name)
        stub = get_internal_grpc_stub(ip, aio=True)
        response = await stub.GetVolumesStat(
            internal_pb2.GetVolumesStatRequest(pool_name=pool_name),
            metadata=[internal_auth_metadata()],
            timeout=15,
        )
        return [
            VolumeStat(
                name=name,
                size=stats.size,
                copy_on_write=stats.copy_on_write,
                thin_provision=stats.thin_provision,
                ready=stats.ready,
                gc_at=stats.gc_at,
                deleted_at=stats.deleted_at,
                created_at=stats.created_at,
                freezefs=stats.freezefs,
                storage_pool=stats.storage_pool,
                img_file=stats.img_file,
                used=stats.used,
                logical_size=stats.logical_size,
                physical_size=stats.physical_size,
            )
            for name, stats in response.stats.items()
        ]

    except NodeUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Selected Node {node_name} Not found",
        )


@router.get("/{volume_name}")
async def get_node_pool_volume(
    node_name: str, pool_name: str, volume_name: str
) -> VolumeStat:
    try:
        ip = node_ip_mapping.get_node_ip(node_name)
        stub = get_internal_grpc_stub(ip, aio=True)
        response = await stub.GetVolumesStat(
            internal_pb2.GetVolumesStatRequest(
                pool_name=pool_name, volume_name=volume_name
            ),
            metadata=[internal_auth_metadata()],
            timeout=15,
        )
        stats = response.stats.get(volume_name, None)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Selected Volume {volume_name} Not found in Pool {pool_name}",
            )

        return VolumeStat(
            name=volume_name,
            size=stats.size,
            copy_on_write=stats.copy_on_write,
            thin_provision=stats.thin_provision,
            ready=stats.ready,
            gc_at=stats.gc_at,
            deleted_at=stats.deleted_at,
            created_at=stats.created_at,
            freezefs=stats.freezefs,
            storage_pool=stats.storage_pool,
            img_file=stats.img_file,
            used=stats.used,
            logical_size=stats.logical_size,
            physical_size=stats.physical_size,
        )

    except NodeUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Selected Node {node_name} Not found",
        )
