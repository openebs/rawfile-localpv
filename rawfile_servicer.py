from pathlib import Path

import grpc
from google.protobuf.wrappers_pb2 import BoolValue

import rawfile_util
from csi import csi_pb2, csi_pb2_grpc
from declarative import be_mounted, be_unmounted, be_symlink, be_absent
from orchestrator.k8s import volume_to_node, run_on_node
from rawfile_util import attach_loop, detach_loops
from remote import init_rawfile, scrub, expand_rawfile
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
                Cap(
                    volume_expansion=Cap.VolumeExpansion(
                        type=Cap.VolumeExpansion.ONLINE
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
            capabilities=[
                Cap(rpc=Cap.RPC(type=Cap.RPC.STAGE_UNSTAGE_VOLUME)),
                Cap(rpc=Cap.RPC(type=Cap.RPC.EXPAND_VOLUME)),
            ]
        )

    @log_grpc_request
    def NodePublishVolume(self, request, context):
        mount_path = request.target_path
        staging_path = request.staging_target_path
        be_mounted(dev=f"{staging_path}/device", mountpoint=mount_path)
        return csi_pb2.NodePublishVolumeResponse()

    @log_grpc_request
    def NodeUnpublishVolume(self, request, context):
        mount_path = request.target_path
        be_unmounted(mount_path)
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
        be_symlink(path=device_path, to=loop_file)
        mount_path = Path(f"{staging_path}/mount")
        mount_path.mkdir(exist_ok=True)
        be_mounted(dev=device_path, mountpoint=mount_path)
        return csi_pb2.NodeStageVolumeResponse()

    @log_grpc_request
    def NodeUnstageVolume(self, request, context):
        img_file = rawfile_util.img_file(request.volume_id)
        staging_path = request.staging_target_path
        mount_path = Path(f"{staging_path}/mount")
        be_unmounted(mount_path)
        be_absent(mount_path)
        device_path = Path(f"{staging_path}/device")
        be_absent(device_path)
        detach_loops(img_file)
        return csi_pb2.NodeUnstageVolumeResponse()

    @log_grpc_request
    def NodeExpandVolume(self, request, context):
        volume_id = request.volume_id
        volume_path = request.volume_path
        size = request.capacity_range.required_bytes
        fs_type = rawfile_util.metadata(volume_id)["fs_type"]
        img_file = rawfile_util.img_file(volume_id)
        for dev in rawfile_util.attached_loops(img_file):
            run(f"losetup -c {dev}")
            if fs_type == "ext4":
                run(f"resize2fs {dev}")
            elif fs_type == "btrfs":
                run(f"btrfs filesystem resize max {volume_path}")
            else:
                raise Exception(f"Unsupported fsType: {fs_type}")
            break
        return csi_pb2.NodeExpandVolumeResponse(capacity_bytes=size)


class RawFileControllerServicer(csi_pb2_grpc.ControllerServicer):
    @log_grpc_request
    def ControllerGetCapabilities(self, request, context):
        Cap = csi_pb2.ControllerServiceCapability
        return csi_pb2.ControllerGetCapabilitiesResponse(
            capabilities=[
                Cap(rpc=Cap.RPC(type=Cap.RPC.CREATE_DELETE_VOLUME)),
                Cap(rpc=Cap.RPC(type=Cap.RPC.EXPAND_VOLUME)),
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

        access_type = volume_capability.WhichOneof("access_type")
        if access_type == "mount":
            fs_type = volume_capability.mount.fs_type
            if fs_type == "":
                fs_type = "ext4"
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
            init_rawfile.as_cmd(volume_id=request.name, size=size, fs_type=fs_type),
            node=node_name,
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

    @log_grpc_request
    def ControllerExpandVolume(self, request, context):
        volume_id = request.volume_id
        node_name = volume_to_node(volume_id)
        size = request.capacity_range.required_bytes
        run_on_node(
            expand_rawfile.as_cmd(volume_id=volume_id, size=size), node=node_name
        )

        return csi_pb2.ControllerExpandVolumeResponse(
            capacity_bytes=size, node_expansion_required=True,
        )
