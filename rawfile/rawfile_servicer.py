import time
from pathlib import Path

import grpc
import utils.rawfile
import utils.storage_pool
from analytics.ga4 import Usage, send_event
from config import config
from consts import (
    CSI_K8S_PVC_NAME_KEY,
    FORMAT_OPTIONS_KEY,
    PROVISIONER_NAME,
    PROVISIONER_VERSION,
)
from csi import csi_pb2, csi_pb2_grpc
from google.protobuf.wrappers_pb2 import BoolValue
from internal import internal_pb2
from orchestrator.k8s import node_ip_mapping, volume_to_node
from utils.commands import run
from utils.devices import device_stats, mountpoint_to_dev
from utils.errors import (
    UnsupportedAccessTypeError,
    VolumeInUseError,
    VolumeNotReadyError,
)
from utils.logs import GRPCLogger, logger
from utils.rawfile import (
    AccessType,
    attach_loop,
    be_absent,
    be_symlink,
    detach_loops,
    metadata,
    metadata_or,
)
from utils.remote import get_capacity, get_internal_grpc_stub, internal_auth_metadata
from utils.task_manager import TaskManager, TaskName
from utils.units import normalize_parameters, str_to_bool
from utils.volume_manager import VolumeSource
from utils.volume_manager import manager as volume_manager

NODE_NAME_TOPOLOGY_KEY = "hostname"
log_grpc_request = GRPCLogger(server_name="rawfile-servicer")


def get_access_type(request):
    access_type = request.volume_capability.WhichOneof("access_type")
    return check_access_type(access_type)


def check_access_type(access_type):
    try:
        return AccessType[access_type]
    except KeyError:
        raise UnsupportedAccessTypeError(access_type)


class RawFileIdentityServicer(csi_pb2_grpc.IdentityServicer):
    @log_grpc_request
    def GetPluginInfo(self, request, context):
        return csi_pb2.GetPluginInfoResponse(
            name=PROVISIONER_NAME, vendor_version=PROVISIONER_VERSION
        )

    @log_grpc_request
    def GetPluginCapabilities(self, request, context):
        Cap = csi_pb2.PluginCapability
        capabilities = [
            Cap(service=Cap.Service(type=Cap.Service.CONTROLLER_SERVICE)),
            Cap(service=Cap.Service(type=Cap.Service.VOLUME_ACCESSIBILITY_CONSTRAINTS)),
        ]
        if config.csi_driver.capabilities.resize.enabled:
            capabilities.extend(
                [
                    Cap(
                        volume_expansion=Cap.VolumeExpansion(
                            type=Cap.VolumeExpansion.ONLINE
                        )
                    )
                ]
            )

        return csi_pb2.GetPluginCapabilitiesResponse(capabilities=capabilities)

    # @log_grpc_request
    def Probe(self, request, context):
        return csi_pb2.ProbeResponse(ready=BoolValue(value=True))


class RawFileNodeServicer(csi_pb2_grpc.NodeServicer):
    def __init__(self, node_name):
        self.node_name = node_name

    # @log_grpc_request
    def NodeGetCapabilities(self, request, context):
        Cap = csi_pb2.NodeServiceCapability
        capabilities = [
            Cap(rpc=Cap.RPC(type=Cap.RPC.STAGE_UNSTAGE_VOLUME)),
            Cap(rpc=Cap.RPC(type=Cap.RPC.GET_VOLUME_STATS)),
        ]
        if config.csi_driver.capabilities.resize.enabled:
            capabilities.extend(
                [
                    Cap(rpc=Cap.RPC(type=Cap.RPC.EXPAND_VOLUME)),
                ]
            )
        return csi_pb2.NodeGetCapabilitiesResponse(capabilities=capabilities)

    @log_grpc_request
    def NodePublishVolume(self, request, context):
        target_path = request.target_path
        staging_path = request.staging_target_path
        staging_dev_path = Path(f"{staging_path}/dev")
        be_symlink(path=target_path, to=staging_dev_path)
        return csi_pb2.NodePublishVolumeResponse()

    @log_grpc_request
    def NodeUnpublishVolume(self, request, context):
        target_path = request.target_path
        be_absent(path=target_path)
        return csi_pb2.NodeUnpublishVolumeResponse()

    @log_grpc_request
    def NodeGetInfo(self, request, context):
        return csi_pb2.NodeGetInfoResponse(
            node_id=self.node_name,
            accessible_topology=csi_pb2.Topology(
                segments={NODE_NAME_TOPOLOGY_KEY: self.node_name}
            ),
        )

    @log_grpc_request
    def NodeStageVolume(self, request, context):
        if not metadata_or(volume_id=request.volume_id).get("ready", False):
            raise VolumeNotReadyError(request.volume_id)
        img_file = utils.rawfile.img_file(request.volume_id)
        loop_file = attach_loop(img_file)
        staging_path = request.staging_target_path
        staging_dev_path = Path(f"{staging_path}/dev")
        be_symlink(path=staging_dev_path, to=loop_file)
        return csi_pb2.NodeStageVolumeResponse()

    @log_grpc_request
    def NodeUnstageVolume(self, request, context):
        img_file = utils.rawfile.img_file(request.volume_id)
        staging_path = request.staging_target_path
        staging_dev_path = Path(f"{staging_path}/dev")
        be_absent(staging_dev_path)
        detach_loops(img_file)
        return csi_pb2.NodeUnstageVolumeResponse()

    # @log_grpc_request
    def NodeGetVolumeStats(self, request, context):
        volume_path = request.volume_path
        if Path(volume_path).is_block_device():
            dev = volume_path
        else:
            dev = mountpoint_to_dev(volume_path)
        stats = device_stats(dev=dev)
        return csi_pb2.NodeGetVolumeStatsResponse(
            usage=[
                csi_pb2.VolumeUsage(
                    total=stats["dev_size"],
                    unit=csi_pb2.VolumeUsage.Unit.BYTES,
                ),
            ]
        )

    @log_grpc_request
    def NodeExpandVolume(self, request, context):
        if not config.csi_driver.capabilities.resize.enabled:
            context.abort(
                grpc.StatusCode.UNIMPLEMENTED,
                "Resizing capabilities are disabled.",
            )

        volume_path = request.volume_path
        size = request.capacity_range.required_bytes
        volume_path = Path(volume_path).resolve()
        run(f"losetup -c {volume_path}")
        return csi_pb2.NodeExpandVolumeResponse(capacity_bytes=size)


class RawFileControllerServicer(csi_pb2_grpc.ControllerServicer):
    def __init__(self, task_manager: TaskManager) -> None:
        super().__init__()
        self._task_manager = task_manager

    @log_grpc_request
    def ControllerGetCapabilities(self, request, context):
        Cap = csi_pb2.ControllerServiceCapability
        capabilities = [
            Cap(rpc=Cap.RPC(type=Cap.RPC.CREATE_DELETE_VOLUME)),
            Cap(rpc=Cap.RPC(type=Cap.RPC.GET_CAPACITY)),
        ]
        if config.csi_driver.capabilities.snapshots.enabled:
            capabilities.extend(
                [
                    Cap(rpc=Cap.RPC(type=Cap.RPC.CREATE_DELETE_SNAPSHOT)),
                    Cap(rpc=Cap.RPC(type=Cap.RPC.LIST_SNAPSHOTS)),
                    Cap(rpc=Cap.RPC(type=Cap.RPC.CLONE_VOLUME)),
                ]
            )
        if config.csi_driver.capabilities.resize.enabled:
            capabilities.extend(
                [
                    Cap(rpc=Cap.RPC(type=Cap.RPC.EXPAND_VOLUME)),
                ]
            )

        return csi_pb2.ControllerGetCapabilitiesResponse(capabilities=capabilities)

    @log_grpc_request
    def CreateVolume(self, request: csi_pb2.CreateVolumeRequest, context):
        size = request.capacity_range.required_bytes
        params = normalize_parameters(request.parameters)
        thin_provision = str_to_bool(params.get("thinprovision", "no"))
        format_options = params.get("formatoptions", "").strip()
        copy_on_write_param = params.get("copyonwrite", None)
        copy_on_write = None
        if copy_on_write_param is not None:
            copy_on_write = str_to_bool(copy_on_write_param)
        freezefs = str_to_bool(params.get("freezefs", "no"))
        storage_pool = params.get("storagepool", config.csi_driver.default_pool)
        if storage_pool not in config.csi_driver.storage_pools:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Invalid storage pool '{storage_pool}'. Available pools: {list(config.csi_driver.storage_pools.keys())}",
            )
        source_type = None
        source_id = None
        node_name = None
        try:
            node_name = request.accessibility_requirements.preferred[0].segments[
                NODE_NAME_TOPOLOGY_KEY
            ]
        except IndexError:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "No preferred topology set. Is external-provisioner running in strict-topology mode?",
            )
        except KeyError:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "Topology key not found... why?"
            )
        required_space = size
        if request.volume_content_source:
            if all(
                (
                    request.volume_content_source.snapshot,
                    request.volume_content_source.snapshot.snapshot_id,
                )
            ):
                source_type = VolumeSource.snapshot
                source_id = request.volume_content_source.snapshot.snapshot_id
            elif all(
                (
                    request.volume_content_source.volume,
                    request.volume_content_source.volume.volume_id,
                )
            ):
                source_type = VolumeSource.volume
                source_id = request.volume_content_source.volume.volume_id
                required_space = required_space * 3

        if not config.csi_driver.capabilities.snapshots.enabled and (
            source_type == VolumeSource.volume or source_type == VolumeSource.snapshot
        ):
            context.abort(
                grpc.StatusCode.UNIMPLEMENTED,
                "Snapshotting capabilities are disabled.",
            )

        if utils.storage_pool.get_capacity(storage_pool) < required_space:
            context.abort(
                grpc.StatusCode.RESOURCE_EXHAUSTED,
                "Insufficient disk space (Cloning a volume requires at least 3× the volume size).",
            )
        is_ready = False
        try:
            is_ready = metadata(request.name).get("ready", False)
        except FileNotFoundError:
            self._task_manager.run_task(
                TaskName.CREATE_VOLUME,
                request.name,
                size,
                storage_pool,
                thin_provision,
                freezefs,
                copy_on_write,
                source_type,
                source_id,
            )
        start_time = time.time()
        logger.info(
            "Waiting for volume to be ready", name=request.name, is_ready=is_ready
        )
        while time.time() - start_time < 30:
            is_ready = metadata_or(request.name).get("ready", False)
            if is_ready:
                break
            time.sleep(0.5)

        if not is_ready:
            context.abort(grpc.StatusCode.DEADLINE_EXCEEDED, "Volume Still Creating...")
            return

        def volume_provision(usage: Usage):
            pvc_name = params.get(CSI_K8S_PVC_NAME_KEY, "")
            usage.volume_provision(pvc_name, request.name, size)

        send_event(volume_provision)

        return csi_pb2.CreateVolumeResponse(
            volume=csi_pb2.Volume(
                volume_id=request.name,
                volume_context={FORMAT_OPTIONS_KEY: format_options},
                capacity_bytes=size,
                accessible_topology=[
                    csi_pb2.Topology(segments={NODE_NAME_TOPOLOGY_KEY: node_name})
                ],
                content_source=request.volume_content_source,
            )
        )

    @log_grpc_request
    def DeleteVolume(self, request: csi_pb2.DeleteVolumeRequest, context):
        try:
            img_size = volume_manager.delete_volume(request.volume_id)

            def volume_deprovision(usage: Usage):
                if img_size > 0:
                    usage.volume_deprovision(request.volume_id, img_size)

            send_event(volume_deprovision)
            return csi_pb2.DeleteVolumeResponse()
        except VolumeInUseError:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, "Volume in use")

    def GetCapacity(self, request: csi_pb2.GetCapacityRequest, context):
        params = normalize_parameters(request.parameters)
        storage_pool = params.get("storagepool", config.csi_driver.default_pool)
        if storage_pool not in config.csi_driver.storage_pools:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Invalid storage pool '{storage_pool}'. Available pools: {list(config.csi_driver.storage_pools.keys())}",
            )
        return csi_pb2.GetCapacityResponse(
            available_capacity=int(get_capacity(storage_pool)),
        )

    @log_grpc_request
    def ControllerExpandVolume(self, request, context):
        if not config.csi_driver.capabilities.resize.enabled:
            context.abort(
                grpc.StatusCode.UNIMPLEMENTED,
                "Resizing capabilities are disabled.",
            )

        volume_id = request.volume_id
        node_name = volume_to_node(volume_id)
        size = request.capacity_range.required_bytes

        node_ip_str = node_ip_mapping.get_node_ip(node_name)
        stub = get_internal_grpc_stub(node_ip_str)
        response = stub.ExpandRawFile(
            internal_pb2.ExpandRawFileRequest(volume_id=volume_id, new_size=size),
            metadata=[internal_auth_metadata()],
            timeout=15,
        )

        if response.status == internal_pb2.ExpandRawFileStatus.RESOURCE_EXHAUSTED:
            context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, "Not enough disk space")

        node_expansion_required = True
        if get_access_type(request) is AccessType.block:
            node_expansion_required = response.is_attached

        return csi_pb2.ControllerExpandVolumeResponse(
            capacity_bytes=size,
            # unstaged block volumes don't require node expansion
            node_expansion_required=node_expansion_required,
        )
