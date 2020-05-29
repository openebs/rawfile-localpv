from pathlib import Path

import grpc
from google.protobuf.wrappers_pb2 import BoolValue

import rawfile_util
from csi import csi_pb2, csi_pb2_grpc
from orchestrator.k8s import volume_to_node, run_on_node
from rawfile_util import attach_loop, detach_loops
from remote import init_rawfile, scrub
from util import log_grpc_request, run

NODE_NAME_TOPOLOGY_KEY = "hostname"


class RawFileIdentityServicer(csi_pb2_grpc.IdentityServicer):
    @log_grpc_request
    def GetPluginInfo(self, request, context):
        return csi_pb2.GetPluginInfoResponse(
            name="rawfile.hamravesh.com", vendor_version="0.0.1"
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
            ]
        )

    @log_grpc_request
    def Probe(self, request, context):
        return csi_pb2.ProbeResponse(ready=BoolValue(value=True))


class RawFileNodeServicer(csi_pb2_grpc.NodeServicer):
    def __init__(self, node_name):
        self.node_name = node_name

    @log_grpc_request
    def NodeGetCapabilities(self, request, context):
        Cap = csi_pb2.NodeServiceCapability
        return csi_pb2.NodeGetCapabilitiesResponse(
            capabilities=[Cap(rpc=Cap.RPC(type=Cap.RPC.STAGE_UNSTAGE_VOLUME))]
        )

    @log_grpc_request
    def NodePublishVolume(self, request, context):
        mount_path = request.target_path
        staging_path = request.staging_target_path
        run(f"mount --bind {staging_path}/mount {mount_path}")
        return csi_pb2.NodePublishVolumeResponse()

    @log_grpc_request
    def NodeUnpublishVolume(self, request, context):
        mount_path = request.target_path
        run(f"umount {mount_path}")
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
        device_path = Path(f"{staging_path}/device")
        if not device_path.exists():
            device_path.symlink_to(loop_file)
        mount_path = Path(f"{staging_path}/mount")
        if not mount_path.exists():
            mount_path.mkdir()
            run(f"mount {device_path} {mount_path}")
        return csi_pb2.NodeStageVolumeResponse()

    @log_grpc_request
    def NodeUnstageVolume(self, request, context):
        img_file = rawfile_util.img_file(request.volume_id)
        staging_path = request.staging_target_path
        mount_path = Path(f"{staging_path}/mount")
        if mount_path.exists():
            run(f"umount {mount_path}")
            mount_path.rmdir()
        device_path = Path(f"{staging_path}/device")
        if device_path.exists():
            device_path.unlink()
        detach_loops(img_file)
        return csi_pb2.NodeUnstageVolumeResponse()


class RawFileControllerServicer(csi_pb2_grpc.ControllerServicer):
    @log_grpc_request
    def ControllerGetCapabilities(self, request, context):
        Cap = csi_pb2.ControllerServiceCapability
        return csi_pb2.ControllerGetCapabilitiesResponse(
            capabilities=[Cap(rpc=Cap.RPC(type=Cap.RPC.CREATE_DELETE_VOLUME))]
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

        access_type = volume_capability.WhichOneof("access_type")
        if access_type == "mount":
            pass
        elif access_type == "block":
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "Block mode not supported (yet)"
            )
        else:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, f"Unknown access type: {access_type}"
            )

        size = request.capacity_range.required_bytes
        size = max(size, 10 * 1024 * 1024)  # At least 10MB

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

        run_on_node(
            init_rawfile.as_cmd(volume_id=request.name, size=size), node=node_name
        )

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
        node_name = volume_to_node(request.volume_id)
        run_on_node(scrub.as_cmd(volume_id=request.volume_id), node=node_name)
        return csi_pb2.DeleteVolumeResponse()
