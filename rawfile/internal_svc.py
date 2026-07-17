import time
from typing import Final

import consts
import grpc
from config import config
from consts import COW_SUPPORT_MAP
from internal import internal_pb2, internal_pb2_grpc
from utils.lock import VolLock
from utils.logs import GRPCLogger, logger
from utils.rawfile import (
    fallocate,
    img_file,
    metadata,
    metadata_or,
    patch_metadata,
    snapshots_dir,
    truncate,
)
from utils.storage_pool import get_capacity
from utils.task_manager import TaskManager
from utils.volume_manager import manager as volume_manager

SIGNATURE_METADATA: Final[str] = "x-signature"
log_grpc_request = GRPCLogger(server_name="internal")


class SignatureInterceptor(grpc.ServerInterceptor):
    def __init__(self, signature: str | None = None):
        self.signature = signature

        def abort(ignored_request, context):
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid signature")

        self._abort_handler = grpc.unary_unary_rpc_method_handler(abort)

    def intercept_service(self, continuation, handler_call_details):
        if self.signature:
            expected_metadata = (SIGNATURE_METADATA, self.signature)

            if expected_metadata in handler_call_details.invocation_metadata:
                return continuation(handler_call_details)

            else:
                logger.debug(
                    "SignatureInterceptor: Invalid signature",
                    metadata=handler_call_details.invocation_metadata,
                )
                return self._abort_handler
        else:
            return continuation(handler_call_details)


class InternalServicer(internal_pb2_grpc.InternalServicer):
    def __init__(self, task_manager: TaskManager):
        self._task_manager = task_manager

    @log_grpc_request
    def ExpandRawFile(
        self, request: internal_pb2.ExpandRawFileRequest, context
    ) -> internal_pb2.ExpandRawFileResponse:
        with VolLock(request.volume_id):
            img_file_path = img_file(request.volume_id)
            size_inc = request.new_size - metadata(request.volume_id)["size"]
            if size_inc <= 0:
                return internal_pb2.ExpandRawFileResponse(
                    is_attached=volume_manager.is_attached(request.volume_id),
                    status=internal_pb2.ExpandRawFileStatus.OK,
                )
            meta = metadata(request.volume_id)
            if get_capacity(meta["storage_pool"]) < request.new_size:
                return internal_pb2.ExpandRawFileResponse(
                    is_attached=volume_manager.is_attached(request.volume_id),
                    status=internal_pb2.ExpandRawFileStatus.RESOURCE_EXHAUSTED,
                )
            if meta.get("thin_provision", False):
                truncate(img_file_path, request.new_size)
            else:
                fallocate(img_file_path, request.new_size)
            patch_metadata(
                request.volume_id,
                meta["storage_pool"],
                {"size": request.new_size},
            )
            return internal_pb2.ExpandRawFileResponse(
                is_attached=volume_manager.is_attached(request.volume_id),
                status=internal_pb2.ExpandRawFileStatus.OK,
            )

    @log_grpc_request
    def GetRawFile(self, request: internal_pb2.GetRawFileRequest, context):
        volume_metadata = metadata(request.volume_id)
        snapshot_id = request.snapshot_id or f"tmp-snapshot-{int(time.time())}"
        if not request.with_data:
            return internal_pb2.GetRawFileResponse(
                metadata=volume_metadata,
                data=None,
            )

        with open(snapshots_dir(request.volume_id) / f"{snapshot_id}.img", "rb") as f:
            while chunk := f.read(1024 * 1024):  # 1MB
                yield internal_pb2.GetRawFileResponse(
                    metadata=volume_metadata, data=chunk
                )

    @log_grpc_request
    def GetPoolsStats(self, request: internal_pb2.GetPoolsStatsRequest, context):
        return internal_pb2.GetPoolsStatsResponse(
            stats={
                name: internal_pb2.PoolStat(
                    reserved_capacity=pool.reserved_capacity
                    if isinstance(pool.reserved_capacity, str)
                    else str(pool.reserved_capacity.to("B")),
                    path=pool.path.as_posix(),
                    reserved_capacity_mode=pool.reserved_capacity_mode,
                    capacity=get_capacity(name),
                    copy_on_write_supported=COW_SUPPORT_MAP.get(name, False),
                )
                for name, pool in (config.csi_driver.storage_pools or {}).items()
            }
        )

    @log_grpc_request
    def GetVolumesStat(self, request: internal_pb2.GetVolumesStatRequest, context):
        stats = {}
        volumes = []
        if request.volume_name:
            volumes = [request.volume_name]
        else:
            volumes = volume_manager.list_all_volumes()
        for volname in volumes:
            meta = metadata_or(volname)
            if not meta:
                continue
            if request.pool_name and meta.get("storage_pool") != request.pool_name:
                continue
            size_stats = volume_manager.get_volume_stats(volname)
            if not size_stats:
                continue
            copy_on_write_param = meta.get("copy_on_write", None)
            copy_on_write = (
                copy_on_write_param
                if copy_on_write_param is not None
                else consts.COW_SUPPORT_MAP.get(meta.get("storage_pool", None), False)
            )
            stats[volname] = internal_pb2.VolumeStat(
                name=volname,
                size=meta["size"],
                copy_on_write=copy_on_write,
                thin_provision=meta["thin_provision"],
                ready=meta["ready"],
                deleted_at=meta.get("deleted_at", None),
                created_at=meta["created_at"],
                gc_at=meta.get("gc_at", None),
                freezefs=meta.get("freezefs", False),
                storage_pool=meta["storage_pool"],
                img_file=meta["img_file"],
                used=size_stats["used"],
                logical_size=size_stats["logical_size"],
                physical_size=size_stats["physical_size"],
            )
        return internal_pb2.GetVolumesStatResponse(stats=stats)

    @log_grpc_request
    def GetNodeTasks(self, request: internal_pb2.GetNodeTasksRequest, context):
        # TODO: Add other fields from task state
        return internal_pb2.GetNodeTasksResponse(
            tasks={
                task_id: internal_pb2.Task(
                    task=task_data["task"],
                    args=task_data["args"],
                    kwargs=task_data["kwargs"],
                    retry_count=task_data["retry_count"],
                    state=task_data["state"],
                )
                for task_id, task_data in self._task_manager.get_tasks().items()
            }
        )
