from pathlib import Path
from subprocess import CalledProcessError

import grpc
from google.protobuf.wrappers_pb2 import BoolValue

import rawfile_util
from consts import (
    PROVISIONER_VERSION,
    PROVISIONER_NAME,
    RESOURCE_EXHAUSTED_EXIT_CODE,
    VOLUME_IN_USE_EXIT_CODE,
)
from csi import csi_pb2, csi_pb2_grpc
from declarative import be_symlink, be_absent
from fs_util import device_stats, mountpoint_to_dev
from orchestrator.k8s import volume_to_node, run_on_node
from rawfile_util import attach_loop, detach_loops
from remote import init_rawfile, scrub, get_capacity, expand_rawfile
from util import log_grpc_request, run

NODE_NAME_TOPOLOGY_KEY = "hostname"


class RawFileIdentityServicer(csi_pb2_grpc.IdentityServicer):
    @log_grpc_request
    def GetPluginInfo(self, request, context):
        return csi_pb2.GetPluginInfoResponse(
            name=PROVISIONER_NAME, vendor_version=PROVISIONER_VERSION
        )

    @log_grpc_request
    def GetPluginCapabilities(self, request, context):
        Cap = csi_pb2.PluginCapability
        return csi_pb2.GetPluginCapabilitiesResponse(
            capabilities=[
                Cap(service=Cap.Service(type=Cap.Service.CONTROLLER_SERVICE)),
                Cap(
                    service=Cap.Service(
                        type=Cap.Service.VOLUME_ACCESSIBILITY_CONSTRAINTS
                    )
                ),
                Cap(
                    volume_expansion=Cap.VolumeExpansion(
                        type=Cap.VolumeExpansion.ONLINE
                    )
                ),
            ]
        )

    # @log_grpc_request
    def Probe(self, request, context):
        return csi_pb2.ProbeResponse(ready=BoolValue(value=True))


class RawFileNodeServicer(csi_pb2_grpc.NodeServicer):
    def __init__(self, node_name):
        self.node_name = node_name

    # @log_grpc_request
    def NodeGetCapabilities(self, request, context):
        Cap = csi_pb2.NodeServiceCapability
        return csi_pb2.NodeGetCapabilitiesResponse(
            capabilities=[
                Cap(rpc=Cap.RPC(type=Cap.RPC.STAGE_UNSTAGE_VOLUME)),
                Cap(rpc=Cap.RPC(type=Cap.RPC.GET_VOLUME_STATS)),
                Cap(rpc=Cap.RPC(type=Cap.RPC.EXPAND_VOLUME)),
            ]
        )

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
        img_file = rawfile_util.img_file(request.volume_id)
        loop_file = attach_loop(img_file)
        staging_path = request.staging_target_path
        staging_dev_path = Path(f"{staging_path}/dev")
        be_symlink(path=staging_dev_path, to=loop_file)
        return csi_pb2.NodeStageVolumeResponse()

    @log_grpc_request
    def NodeUnstageVolume(self, request, context):
        img_file = rawfile_util.img_file(request.volume_id)
        staging_path = request.staging_target_path
        staging_dev_path = Path(f"{staging_path}/dev")
        be_absent(staging_dev_path)
        detach_loops(img_file)
        return csi_pb2.NodeUnstageVolumeResponse()

    # @log_grpc_request
    def NodeGetVolumeStats(self, request, context):
        volume_path = request.volume_path
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
        volume_path = request.volume_path
        size = request.capacity_range.required_bytes
        volume_path = Path(volume_path).resolve()
        run(f"losetup -c {volume_path}")
        return csi_pb2.NodeExpandVolumeResponse(capacity_bytes=size)


class RawFileControllerServicer(csi_pb2_grpc.ControllerServicer):
    @log_grpc_request
    def ControllerGetCapabilities(self, request, context):
        Cap = csi_pb2.ControllerServiceCapability
        return csi_pb2.ControllerGetCapabilitiesResponse(
            capabilities=[
                Cap(rpc=Cap.RPC(type=Cap.RPC.CREATE_DELETE_VOLUME)),
                Cap(rpc=Cap.RPC(type=Cap.RPC.GET_CAPACITY)),
                Cap(rpc=Cap.RPC(type=Cap.RPC.EXPAND_VOLUME)),
                Cap(rpc=Cap.RPC(type=Cap.RPC.CREATE_DELETE_SNAPSHOT)),
            ]
        )

    @log_grpc_request
    def CreateVolume(self, request, context):
        # TODO: volume_capabilities

        if len(request.volume_capabilities) != 1:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "Exactly one cap is supported"
            )

        volume_capability = request.volume_capabilities[0]

        AccessModeEnum = csi_pb2.VolumeCapability.AccessMode.Mode
        if volume_capability.access_mode.mode not in [
            AccessModeEnum.SINGLE_NODE_WRITER
        ]:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Unsupported access mode: {AccessModeEnum.Name(volume_capability.access_mode.mode)}",
            )

        # FIXME: re-enable access_type after bd2fs is fixed
        # access_type = volume_capability.WhichOneof("access_type")
        # if access_type == "block":
        #     pass
        # else:
        #     context.abort(
        #         grpc.StatusCode.INVALID_ARGUMENT,
        #         "PANIC! This should be handled by bd2fs!",
        #     )

        MIN_SIZE = 16 * 1024 * 1024  # 16MiB: can't format xfs with smaller volumes
        size = max(MIN_SIZE, request.capacity_range.required_bytes)

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

        try:
            init_rawfile(volume_id=request.name, size=size),
        except CalledProcessError as exc:
            if exc.returncode == RESOURCE_EXHAUSTED_EXIT_CODE:
                context.abort(
                    grpc.StatusCode.RESOURCE_EXHAUSTED, "Not enough disk space"
                )
            else:
                raise exc

        return csi_pb2.CreateVolumeResponse(
            volume=csi_pb2.Volume(
                volume_id=request.name,
                capacity_bytes=size,
                accessible_topology=[
                    csi_pb2.Topology(segments={NODE_NAME_TOPOLOGY_KEY: node_name})
                ],
            )
        )

    @log_grpc_request
    def DeleteVolume(self, request, context):
        try:
            scrub(volume_id=request.volume_id)
        except CalledProcessError as exc:
            if exc.returncode == VOLUME_IN_USE_EXIT_CODE:
                context.abort(grpc.StatusCode.FAILED_PRECONDITION, "Volume in use")
            else:
                raise exc
        return csi_pb2.DeleteVolumeResponse()

    def GetCapacity(self, request, context):
        return csi_pb2.GetCapacityResponse(
            available_capacity=get_capacity(),
        )

    @log_grpc_request
    def ControllerExpandVolume(self, request, context):
        volume_id = request.volume_id
        node_name = volume_to_node(volume_id)
        size = request.capacity_range.required_bytes

        try:
            run_on_node(
                expand_rawfile.as_cmd(volume_id=volume_id, size=size), node=node_name
            )
        except CalledProcessError as exc:
            if exc.returncode == RESOURCE_EXHAUSTED_EXIT_CODE:
                context.abort(
                    grpc.StatusCode.RESOURCE_EXHAUSTED, "Not enough disk space"
                )
            else:
                raise exc

        return csi_pb2.ControllerExpandVolumeResponse(
            capacity_bytes=size,
            node_expansion_required=True,
        )
