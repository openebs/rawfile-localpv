import os
import time
from dataclasses import dataclass
from glob import glob
from pathlib import Path

import consts
from config import config
from filesystem import from_device as fs_from_device

from utils.commands import run
from utils.errors import FsFreezeNotSupportedOnBlockVolumes, SnapshotCreateVolumeInUse
from utils.lock import VolLock
from utils.rawfile import (
    attached_loops,
    img_file,
    is_cow_supported,
    metadata,
    snapshots_dir,
)


@dataclass
class Snapshot:
    name: str
    volume_id: str
    size_bytes: int
    creation_time: float
    snapshot_id: str
    ready: bool
    temporary: bool


@dataclass
class SnapshotList:
    data: list[Snapshot]
    next_token: int | None


class SnapshotManager:
    def _get_snapshot_path(
        self, volume_id: str, name: str, temporary: bool = False
    ) -> Path:
        return snapshots_dir(volume_id, temporary=temporary) / f"{name}.img"

    def create_snapshot(
        self,
        volume_id: str,
        name: str,
        copy_on_write: bool,
        freeze_fs: bool = False,
        temporary: bool = False,
    ) -> Snapshot:
        with VolLock(volume_id):
            file = img_file(volume_id)
            loop_devs = attached_loops(file.as_posix())
            snap_path = self._get_snapshot_path(volume_id, name, temporary)
            snap_path.parent.mkdir(parents=True, exist_ok=True)
            Path(f"{snap_path}.creating").touch()
            Path(snap_path).unlink(missing_ok=True)
            snap_inuse = freeze_fs or copy_on_write
            if (loop_devs and len(loop_devs)) and (not snap_inuse):
                raise SnapshotCreateVolumeInUse(volume_id=volume_id, snapshot_name=name)
            try:
                if freeze_fs and loop_devs:
                    for dev in loop_devs:
                        fs = fs_from_device(dev)
                        if not fs:
                            raise FsFreezeNotSupportedOnBlockVolumes()
                        fs.freeze()

                reflink = "always" if copy_on_write else "never"
                cmd = f"cp --sparse=auto --reflink={reflink} {file} {snap_path}"
                run(cmd, check=True)

                creation_time = time.time()
                Path(f"{snap_path}.creating").unlink(missing_ok=True)
                return Snapshot(
                    name=name,
                    volume_id=volume_id,
                    size_bytes=snap_path.stat().st_size,
                    creation_time=creation_time,
                    snapshot_id=f"{volume_id}/{name}",
                    ready=True,
                    temporary=temporary,
                )
            except Exception:
                Path(snap_path).unlink(missing_ok=True)
                raise
            finally:
                if freeze_fs and loop_devs:
                    for dev in loop_devs:
                        fs = fs_from_device(dev)
                        if not fs:
                            raise FsFreezeNotSupportedOnBlockVolumes()
                        fs.unfreeze()

    def delete_snapshot(self, volume_id: str, name: str, temporary: bool = False):
        """Delete a snapshot"""
        with VolLock(volume_id):
            snap_path = self._get_snapshot_path(volume_id, name, temporary)
            for path in (
                snap_path,
                Path(f"{snap_path}.creating"),
            ):
                path.unlink(missing_ok=True)

    def restore_snapshot(
        self, volume_id: str, name: str, destination: Path, temporary: bool = False
    ):
        """Restore a snapshot"""
        volume_meta = metadata(volume_id)
        snap_path = self._get_snapshot_path(volume_id, name, temporary)
        copy_on_write_param = volume_meta.get("copy_on_write", None)
        copy_on_write = (
            copy_on_write_param
            if copy_on_write_param is not None
            else consts.COW_SUPPORT_MAP.get(
                volume_meta.get("storage_pool", None), False
            )
        ) and is_cow_supported(Path(os.path.dirname(snap_path)), destination)
        reflink = "always" if copy_on_write else "never"
        cmd = (
            f"cp --sparse=auto --reflink={reflink} {snap_path} {destination.as_posix()}"
        )
        run(cmd, check=True)

    def list_snapshots(
        self,
        volume_id: str | None = None,
        snapshot_name: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
        ready: bool | None = None,
        temporary: bool = False,
    ) -> SnapshotList:
        """List available snapshots"""
        subdir = "snapshots/temp" if temporary else "snapshots"
        patterns = []
        if volume_id:
            patterns = [
                f"{config.csi_driver.storage_pools[metadata(volume_id)['storage_pool']].path}/{volume_id if volume_id else '**'}/{subdir}/{snapshot_name if snapshot_name else '*'}.img"
            ]
        else:
            for pool in config.csi_driver.storage_pools.values():
                patterns.append(
                    f"{pool.path}/**/{subdir}/{snapshot_name if snapshot_name else '*'}.img"
                )
        snapshots = []
        snapshot_files = []
        for pattern in patterns:
            snapshot_files.extend(sorted(glob(pattern, recursive=True)))

        count = 0
        idx = 0
        for idx, snap_filename in enumerate(snapshot_files):
            if offset and idx < offset:
                continue
            snap_file = Path(snap_filename)
            creating = Path(f"{snap_file}.creating").exists()
            snap_name = snap_file.stem
            vol_id = snap_file.parent.parent.name
            if ready is not None and ready == creating:
                continue
            snapshots.append(
                Snapshot(
                    name=snap_name,
                    volume_id=vol_id,
                    snapshot_id=f"{vol_id}/{snap_name}",
                    size_bytes=snap_file.stat().st_size,
                    creation_time=snap_file.stat().st_ctime,
                    ready=not creating,
                    temporary=temporary,
                )
            )
            count += 1
            if limit and count >= limit:
                break
        next_token = None
        if offset and snapshots and (idx + 1) < len(snapshot_files):
            next_token = offset + len(snapshots)

        return SnapshotList(data=snapshots, next_token=next_token)


manager = SnapshotManager()

__all__ = ["manager"]
