from pathlib import Path

from config import config
from consts import FORMAT_OPTIONS_KEY
import grpc
import time
from csi import csi_pb2, csi_pb2_grpc
from csi.csi_pb2 import (
    CreateVolumeRequest,
    NodeExpandVolumeRequest,
    NodePublishVolumeRequest,
    NodeStageVolumeRequest,
    NodeUnpublishVolumeRequest,
    NodeUnstageVolumeRequest,
)
from declarative import (
    mount,
    unmount,
)
from utils.rawfile import be_absent
from google.protobuf.timestamp_pb2 import Timestamp
from utils.logs import log_grpc_request
from filesystem import get_from_device_or_fallback, from_device
from filesystem.utils import get_device_for_mountpoint
from rawfile_servicer import check_access_type, get_access_type
from utils.rawfile import (
    img_file,
    attach_loop,
    AccessType,
    detach_loops,
)
from utils.devices import path_stats
from filesystem.base import UnknownFileSystemError
from utils.lock import VolLock


class Bd2FsIdentityServicer(csi_pb2_grpc.IdentityServicer):
    def __init__(self, bds: csi_pb2_grpc.IdentityServicer):
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
    def __init__(self, bds: csi_pb2_grpc.NodeServicer):
        self.bds = bds

    # @log_grpc_request
    def NodeGetCapabilities(self, request, context):
        return self.bds.NodeGetCapabilities(request, context)

    @log_grpc_request
    def NodePublishVolume(self, request, context):
        with VolLock(request.volume_id):
            staging_dev = f"{request.staging_target_path}/device"

            path = Path(request.target_path)
            access_type_actions = {
                AccessType.mount: path.mkdir,
                AccessType.block: path.touch,
            }
            access_type_actions[get_access_type(request)](exist_ok=True)
            mount(
                device=staging_dev,
                mountpoint=request.target_path,
                readonly=request.readonly,
                options=request.volume_capability.mount.mount_flags or [],
            )
            return csi_pb2.NodePublishVolumeResponse()

    @log_grpc_request
    def NodeUnpublishVolume(self, request, context):
        with VolLock(request.volume_id):
            unmount(request.target_path, clear_mountpoint=True)
            return csi_pb2.NodeUnpublishVolumeResponse()

    @log_grpc_request
    def NodeGetInfo(self, request, context):
        return self.bds.NodeGetInfo(request, context)

    @log_grpc_request
    def NodeStageVolume(self, request, context):
        with VolLock(request.volume_id):
            bd_stage_request = NodeStageVolumeRequest()
            bd_stage_request.CopyFrom(request)
            block_path = f"{request.staging_target_path}/block"
            device_path = f"{request.staging_target_path}/device"
            bd_stage_request.staging_target_path = block_path
            Path(bd_stage_request.staging_target_path).mkdir(
                exist_ok=True, parents=True
            )
            self.bds.NodeStageVolume(bd_stage_request, context)

            bd_publish_request = NodePublishVolumeRequest()
            bd_publish_request.volume_id = request.volume_id
            bd_publish_request.publish_context.update(request.publish_context)
            bd_publish_request.staging_target_path = (
                bd_stage_request.staging_target_path
            )
            bd_publish_request.target_path = device_path
            bd_publish_request.volume_capability.CopyFrom(request.volume_capability)
            bd_publish_request.readonly = False
            bd_publish_request.secrets.update(request.secrets)
            bd_publish_request.volume_context.update(request.volume_context)

            self.bds.NodePublishVolume(bd_publish_request, context)

            if get_access_type(request) is AccessType.mount:
                format_options_str = bd_publish_request.volume_context.get(
                    FORMAT_OPTIONS_KEY, ""
                )
                format_options = []
                if len(format_options_str):
                    format_options = format_options_str.split(" ")
                default_fs = request.volume_capability.mount.fs_type
                fs = get_from_device_or_fallback(
                    bd_publish_request.target_path, (default_fs or config.default_fs)
                )
                fs.mountpoint = f"{request.staging_target_path}/mount"
                fs.format_and_mount(
                    mount_options=bd_publish_request.volume_capability.mount.mount_flags
                    or [],
                    format_options=format_options,
                )

            return csi_pb2.NodeStageVolumeResponse()

    @log_grpc_request
    def NodeUnstageVolume(self, request, context):
        with VolLock(request.volume_id):
            mount_path = f"{request.staging_target_path}/mount"
            device_path = f"{request.staging_target_path}/device"
            unmount(mount_path, clear_mountpoint=True)

            bd_unpublish_request = NodeUnpublishVolumeRequest()
            bd_unpublish_request.volume_id = request.volume_id
            bd_unpublish_request.target_path = device_path
            self.bds.NodeUnpublishVolume(bd_unpublish_request, context)

            bd_unstage_request = NodeUnstageVolumeRequest()
            bd_unstage_request.CopyFrom(request)
            block_path = f"{request.staging_target_path}/block"
            bd_unstage_request.staging_target_path = block_path
            self.bds.NodeUnstageVolume(bd_unstage_request, context)
            be_absent(bd_unstage_request.staging_target_path)

            return csi_pb2.NodeUnstageVolumeResponse()

    # @log_grpc_request
    def NodeGetVolumeStats(self, request, context):
        volume_path = request.volume_path
        if Path(volume_path).is_block_device():
            return self.bds.NodeGetVolumeStats(request, context)
        stats = path_stats(volume_path)
        return csi_pb2.NodeGetVolumeStatsResponse(
            usage=[
                csi_pb2.VolumeUsage(
                    available=stats["fs_avail"],
                    total=stats["fs_size"],
                    used=stats["fs_size"] - stats["fs_avail"],
                    unit=csi_pb2.VolumeUsage.Unit.BYTES,
                ),
                csi_pb2.VolumeUsage(
                    available=stats["fs_files_avail"],
                    total=stats["fs_files"],
                    used=stats["fs_files"] - stats["fs_files_avail"],
                    unit=csi_pb2.VolumeUsage.Unit.INODES,
                ),
            ]
        )

    @log_grpc_request
    def NodeExpandVolume(self, request, context):
        with VolLock(request.volume_id):
            if get_access_type(request) is AccessType.block:
                device_path = f"{request.staging_target_path}/device"
                request.volume_path = device_path
                self.bds.NodeExpandVolume(request, context)
                size = request.capacity_range.required_bytes
                return csi_pb2.NodeExpandVolumeResponse(capacity_bytes=size)

            # FIXME: hacky way to determine if `volume_path` is staged path,
            # or the mount itself
            # Based on CSI 1.4.0 specifications:
            # > The staging_target_path field is not required,
            # for backwards compatibility,
            # but the CO SHOULD supply it.
            # Apparently, k8s 1.18 does not supply it. So:
            dev_path = get_device_for_mountpoint(request.volume_path)
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
            fs = from_device(dev_path)
            if not fs:
                raise UnknownFileSystemError(device=dev_path)
            fs.mountpoint = volume_path
            fs.resize()

            size = request.capacity_range.required_bytes
            return csi_pb2.NodeExpandVolumeResponse(capacity_bytes=size)


class Bd2FsControllerServicer(csi_pb2_grpc.ControllerServicer):
    def __init__(self, bds: csi_pb2_grpc.ControllerServicer):
        self.bds = bds

    @log_grpc_request
    def ControllerGetCapabilities(self, request, context):
        return self.bds.ControllerGetCapabilities(request, context)

    @log_grpc_request
    def CreateVolume(self, request, context):
        if len(request.volume_capabilities) != 1:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "Exactly one cap is supported"
            )

        volume_capability = request.volume_capabilities[0]

        AccessModeEnum = csi_pb2.VolumeCapability.AccessMode.Mode
        if volume_capability.access_mode.mode not in [
            AccessModeEnum.SINGLE_NODE_WRITER
        ]:
            access_mode = AccessModeEnum.Name(volume_capability.access_mode.mode)
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Unsupported access mode: {access_mode}",
            )

        access_type = volume_capability.WhichOneof("access_type")
        check_access_type(access_type)

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
        try:
            lock = VolLock(request.volume_id)
        except FileNotFoundError:
            return csi_pb2.DeleteVolumeResponse()
        else:
            with lock:
                return self.bds.DeleteVolume(request, context)

    def GetCapacity(self, request, context):
        return self.bds.GetCapacity(request, context)

    @log_grpc_request
    def ControllerExpandVolume(self, request, context):
        response = self.bds.ControllerExpandVolume(request, context)
        return response

    @log_grpc_request
    def CreateSnapshot(self, request: csi_pb2.CreateSnapshotRequest, context):
        with VolLock(request.source_volume_id):
            file = img_file(request.source_volume_id)
            loop_dev = attach_loop(file)
            fs = from_device(loop_dev)
            if not fs:
                raise UnknownFileSystemError(
                    device=loop_dev, volume_id=request.source_volume_id
                )
            fs.create_snapshot(name=request.name)

            if fs.mountpoint is None:
                detach_loops(file)

            creation_time_ns = time.time_ns()
            snapshot_id = f"{request.source_volume_id}/{request.name}"
            # TODO: detach loopdev when we get seperated loop devices
            nano = 10**9
            return csi_pb2.CreateSnapshotResponse(
                snapshot=csi_pb2.Snapshot(
                    size_bytes=0,
                    snapshot_id=snapshot_id,
                    source_volume_id=request.source_volume_id,
                    creation_time=Timestamp(
                        seconds=creation_time_ns // nano, nanos=creation_time_ns % nano
                    ),
                    ready_to_use=True,
                )
            )

    @log_grpc_request
    def DeleteSnapshot(self, request: csi_pb2.DeleteSnapshotRequest, context):
        snapshot_id = request.snapshot_id
        volume_id, name = snapshot_id.rsplit("/", 1)

        try:
            if not img_file(volume_id).exists():
                raise FileNotFoundError
        except FileNotFoundError:
            return csi_pb2.DeleteSnapshotResponse()

        with VolLock(volume_id):
            file = img_file(volume_id)

            loop_dev = attach_loop(file)
            fs = from_device(loop_dev)
            if not fs:
                raise UnknownFileSystemError(device=loop_dev, volume_id=volume_id)
            fs.delete_snapshot(name=name)

            if fs.mountpoint is None:
                detach_loops(file)

            return csi_pb2.DeleteSnapshotResponse()
