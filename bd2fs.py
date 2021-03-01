from pathlib import Path

import grpc

from csi import csi_pb2, csi_pb2_grpc
from csi.csi_pb2 import (
    NodeStageVolumeRequest,
    NodePublishVolumeRequest,
    NodeUnpublishVolumeRequest,
    NodeUnstageVolumeRequest,
    NodeExpandVolumeRequest,
    CreateVolumeRequest,
)
from declarative import (
    be_mounted,
    be_unmounted,
    be_absent,
    be_formatted,
    be_fs_expanded,
    current_fs,
)
from metrics import path_stats, mountpoint_to_dev
from util import log_grpc_request


def get_fs(request):
    fs_type = request.volume_capability.mount.fs_type
    if fs_type == "":
        fs_type = "ext4"
    return fs_type


class Bd2FsIdentityServicer(csi_pb2_grpc.IdentityServicer):
    def __init__(self, bds):
        self.bds = bds

    @log_grpc_request
    def GetPluginInfo(self, request, context):
        return self.bds.GetPluginInfo(request, context)

    @log_grpc_request
    def GetPluginCapabilities(self, request, context):
        return self.bds.GetPluginCapabilities(request, context)

    # @log_grpc_request
    def Probe(self, request, context):
        return self.bds.Probe(request, context)


class Bd2FsNodeServicer(csi_pb2_grpc.NodeServicer):
    def __init__(self, bds):
        self.bds = bds

    # @log_grpc_request
    def NodeGetCapabilities(self, request, context):
        return self.bds.NodeGetCapabilities(request, context)

    @log_grpc_request
    def NodePublishVolume(self, request, context):
        staging_dev = f"{request.staging_target_path}/device"
        Path(request.target_path).mkdir(exist_ok=True)
        be_mounted(dev=staging_dev, mountpoint=request.target_path)
        return csi_pb2.NodePublishVolumeResponse()

    @log_grpc_request
    def NodeUnpublishVolume(self, request, context):
        be_unmounted(request.target_path)
        be_absent(request.target_path)
        return csi_pb2.NodeUnpublishVolumeResponse()

    @log_grpc_request
    def NodeGetInfo(self, request, context):
        return self.bds.NodeGetInfo(request, context)

    @log_grpc_request
    def NodeStageVolume(self, request, context):
        bd_stage_request = NodeStageVolumeRequest()
        bd_stage_request.CopyFrom(request)
        bd_stage_request.staging_target_path = f"{request.staging_target_path}/block"
        Path(bd_stage_request.staging_target_path).mkdir(exist_ok=True)
        self.bds.NodeStageVolume(bd_stage_request, context)

        bd_publish_request = NodePublishVolumeRequest()
        bd_publish_request.volume_id = request.volume_id
        bd_publish_request.publish_context.update(request.publish_context)
        bd_publish_request.staging_target_path = bd_stage_request.staging_target_path
        bd_publish_request.target_path = f"{request.staging_target_path}/device"
        bd_publish_request.volume_capability.CopyFrom(request.volume_capability)
        bd_publish_request.readonly = False
        bd_publish_request.secrets.update(request.secrets)
        bd_publish_request.volume_context.update(request.volume_context)

        self.bds.NodePublishVolume(bd_publish_request, context)

        mount_path = f"{request.staging_target_path}/mount"
        Path(mount_path).mkdir(exist_ok=True)
        be_formatted(dev=bd_publish_request.target_path, fs=get_fs(request))
        be_mounted(dev=bd_publish_request.target_path, mountpoint=mount_path)

        return csi_pb2.NodeStageVolumeResponse()

    @log_grpc_request
    def NodeUnstageVolume(self, request, context):
        mount_path = f"{request.staging_target_path}/mount"
        be_unmounted(mount_path)
        be_absent(mount_path)

        bd_unpublish_request = NodeUnpublishVolumeRequest()
        bd_unpublish_request.volume_id = request.volume_id
        bd_unpublish_request.target_path = f"{request.staging_target_path}/device"
        self.bds.NodeUnpublishVolume(bd_unpublish_request, context)

        bd_unstage_request = NodeUnstageVolumeRequest()
        bd_unstage_request.CopyFrom(request)
        bd_unstage_request.staging_target_path = f"{request.staging_target_path}/block"
        self.bds.NodeUnstageVolume(bd_unstage_request, context)
        be_absent(bd_unstage_request.staging_target_path)

        return csi_pb2.NodeUnstageVolumeResponse()

    # @log_grpc_request
    def NodeGetVolumeStats(self, request, context):
        volume_path = request.volume_path
        stats = path_stats(volume_path)
        return csi_pb2.NodeGetVolumeStatsResponse(
            usage=[
                csi_pb2.VolumeUsage(
                    available=stats["fs_free"],
                    total=stats["fs_size"],
                    used=stats["fs_size"] - stats["fs_free"],
                    unit=csi_pb2.VolumeUsage.Unit.BYTES,
                ),
                csi_pb2.VolumeUsage(
                    available=stats["fs_files_free"],
                    total=stats["fs_files"],
                    used=stats["fs_files"] - stats["fs_files_free"],
                    unit=csi_pb2.VolumeUsage.Unit.INODES,
                ),
            ]
        )

    @log_grpc_request
    def NodeExpandVolume(self, request, context):
        # FIXME: hacky way to determine if `volume_path` is staged path, or the mount itself
        # Based on CSI 1.4.0 specifications:
        # > The staging_target_path field is not required, for backwards compatibility, but the CO SHOULD supply it.
        # Apparently, k8s 1.18 does not supply it. So:
        dev_path = mountpoint_to_dev(request.volume_path)
        volume_path = request.volume_path
        if dev_path is None:
            dev_path = f"{request.volume_path}/device"
            volume_path = f"{request.volume_path}/mount"

        bd_request = NodeExpandVolumeRequest()
        bd_request.CopyFrom(request)
        bd_request.volume_path = dev_path
        self.bds.NodeExpandVolume(bd_request, context)

        # Based on CSI 1.4.0 specifications:
        # > If volume_capability is omitted the SP MAY determine
        # > access_type from given volume_path for the volume and perform
        # > node expansion.
        # Apparently k8s 1.18 omits this field.
        fs_type = current_fs(bd_request.volume_path)
        be_fs_expanded(fs_type, bd_request.volume_path, volume_path)

        size = request.capacity_range.required_bytes
        return csi_pb2.NodeExpandVolumeResponse(capacity_bytes=size)


class Bd2FsControllerServicer(csi_pb2_grpc.ControllerServicer):
    def __init__(self, bds):
        self.bds = bds

    @log_grpc_request
    def ControllerGetCapabilities(self, request, context):
        return self.bds.ControllerGetCapabilities(request, context)

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
        assert access_type == "mount"

        bd_request = CreateVolumeRequest()
        bd_request.CopyFrom(request)
        bd_request.capacity_range.required_bytes = max(
            request.capacity_range.required_bytes, 10 * 1024 * 1024
        )  # At least 10MB
        # FIXME: update access_type
        # bd_request.volume_capabilities[0].block = ""
        # bd_request.volume_capabilities[0].mount = None
        return self.bds.CreateVolume(bd_request, context)

    @log_grpc_request
    def DeleteVolume(self, request, context):
        return self.bds.DeleteVolume(request, context)

    @log_grpc_request
    def ControllerExpandVolume(self, request, context):
        response = self.bds.ControllerExpandVolume(request, context)
        assert response.node_expansion_required
        return response
