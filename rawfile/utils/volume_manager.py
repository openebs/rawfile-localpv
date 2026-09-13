import shutil
import time
from enum import Enum
from glob import glob
from os.path import basename, dirname, getsize
from pathlib import Path
from typing import TypedDict

import consts
from config import config
from volume_schema import LATEST_SCHEMA_VERSION, migrate_to

from utils.devices import device_to_mountpoint, stat, statvfs
from utils.errors import SourceTypeRequired, VolumeInUseError, VolumeSourceIsNotReady
from utils.lock import VolLock
from utils.logs import logger
from utils.rawfile import (
    attached_loops,
    fallocate,
    img_file,
    img_size,
    meta_dir,
    metadata,
    metadata_or,
    patch_metadata,
    snapshots_dir,
    truncate,
    update_metadata,
)
from utils.snapshot_manager import manager as snapshot_manager


class VolumeSource(int, Enum):
    snapshot = 1
    volume = 2


class VolumeStats(TypedDict):
    physical_size: int
    logical_size: int
    used: int
    pool: str
    thin_provision: bool
    sparse: bool


class VolumeManager:
    def _get_volume_path(self, storage_pool: str, volume_id: str) -> Path:
        return Path(f"{config.csi_driver.storage_pools[storage_pool].path}/{volume_id}")

    def create_volume(
        self,
        volume_id: str,
        size: int,
        storage_pool: str,
        thin_provision: bool,
        freezefs: bool | None = None,
        copy_on_write: bool | None = None,
        source_type: VolumeSource | None = None,
        source_id: str | None = None,
    ):
        if source_id and (not source_type):
            raise SourceTypeRequired(source_id)
        snapshot_name = None
        source_volume_id = None
        img_data_dir = self._get_volume_path(storage_pool, volume_id)
        img_data_dir.mkdir(mode=consts.D_PERMS, exist_ok=True)
        meta_dir(volume_id).mkdir(exist_ok=True, parents=True)
        patch_metadata(
            volume_id,
            storage_pool,
            {
                "schema_version": LATEST_SCHEMA_VERSION,
                "storage_pool": storage_pool,
                "ready": False,
            },
        )
        try:
            if source_type == VolumeSource.snapshot and source_id:
                source_volume_id, snapshot_name = source_id.rsplit("/", 1)
            elif source_type == VolumeSource.volume and source_id:
                source_volume_id = source_id
                snapshot_name = f"{volume_id}-clone-source"
                source_volume_id = source_id
                source_meta = metadata_or(source_id)
                if not source_meta.get("ready", False):
                    raise VolumeSourceIsNotReady(
                        volume_id, source_volume_id, snapshot_name
                    )
                current_snapshot = snapshot_manager.list_snapshots(
                    volume_id=source_volume_id,
                    snapshot_name=snapshot_name,
                    temporary=True,
                )
                if not (current_snapshot.data and current_snapshot.data[0].ready):
                    snapshot_manager.create_snapshot(
                        volume_id=source_volume_id,
                        name=snapshot_name,
                        temporary=True,
                        copy_on_write=source_meta.get("copy_on_write", None)
                        if source_meta.get("copy_on_write", None) is not None
                        else (
                            consts.COW_SUPPORT_MAP.get(
                                source_meta["storage_pool"], False
                            )
                        ),
                        freeze_fs=source_meta.get("freezefs", False),
                    )
            with VolLock(volume_id):
                img_file = img_data_dir / "disk.img"
                if img_file.exists() and getsize(img_file) >= size:
                    return
                snapshots_dir = Path(img_data_dir.joinpath("snapshots"))
                snapshots_dir.mkdir(exist_ok=True, parents=True)
                snapshots_dir.joinpath("temp").mkdir(exist_ok=True, parents=True)
                patch_metadata(
                    volume_id,
                    storage_pool,
                    {
                        "volume_id": volume_id,
                        "created_at": time.time(),
                        "img_file": img_file.as_posix(),
                        "snapshots_dir": snapshots_dir.as_posix(),
                        "size": size,
                        "thin_provision": thin_provision,
                        "freezefs": freezefs,
                        "copy_on_write": copy_on_write,
                        "storage_pool": storage_pool,
                    },
                )
                img_file.touch()
                if snapshot_name and source_volume_id:
                    snapshots = snapshot_manager.list_snapshots(
                        source_volume_id,
                        snapshot_name,
                        temporary=source_type == VolumeSource.volume,
                    ).data
                    if not (snapshots and snapshots[0].ready):
                        raise VolumeSourceIsNotReady(
                            volume_id, source_volume_id, snapshot_name
                        )
                    source_meta = metadata(source_volume_id)
                    size = max(size, source_meta["size"])
                    thin_provision = source_meta.get("thin_provision", False)
                    logger.info(
                        "Cloning volume data",
                        source_volume=source_volume_id,
                        source_snapshot=snapshot_name,
                    )
                    snapshot_manager.restore_snapshot(
                        source_volume_id,
                        snapshot_name,
                        img_file,
                        source_type == VolumeSource.volume,
                    )
                if thin_provision:
                    truncate(img_file, size)
                else:
                    fallocate(img_file, size)
                patch_metadata(volume_id, storage_pool, {"ready": True})
        finally:
            if source_type == VolumeSource.volume and (
                source_volume_id and snapshot_name
            ):
                snapshot_manager.delete_snapshot(
                    volume_id=source_volume_id, name=snapshot_name, temporary=True
                )
        logger.info("Initialized volume", volume_id=volume_id, size=size)

    def destroy_volume(self, volume_id, dry_run=False):
        def rmdir(path: Path):
            try:
                path.rmdir()
            except FileNotFoundError:
                pass

        logger.info("Destroying Volume", volume_id=volume_id, dry_run=dry_run)
        if dry_run:
            return
        snapshots = list(snapshots_dir(volume_id).glob("*"))
        # don't count the temporary dir!
        snapshots.remove(snapshots_dir(volume_id, temporary=True))
        temp_snapshots = list(snapshots_dir(volume_id, temporary=True).glob("*"))
        total_snapshots = len(snapshots) + len(temp_snapshots)
        meta = metadata_or(volume_id)
        if total_snapshots > 0:
            logger.warning(
                "Volume has Snapshots attached, will only remove volume data",
                volume_id=volume_id,
                snapshots=total_snapshots,
            )
        Path(img_file(volume_id)).unlink(missing_ok=True)
        if not len(temp_snapshots):
            rmdir(snapshots_dir(volume_id, temporary=True))
            if not len(snapshots):
                rmdir(snapshots_dir(volume_id))
        if not total_snapshots:
            # Keep metadata if there are snapshots to be able to delete them later
            for file in meta_dir(volume_id).glob("*"):
                file.unlink(missing_ok=True)
            rmdir(meta_dir(volume_id))
            rmdir(
                self._get_volume_path(
                    meta.get("storage_pool", config.csi_driver.default_pool), volume_id
                )
            )

    def gc_if_needed(self, volume_id, dry_run=True):
        with VolLock(volume_id):
            meta = metadata_or(volume_id)
        deleted_at = meta.get("deleted_at", None)
        gc_at = meta.get("gc_at", None)
        if deleted_at is None or gc_at is None:
            return False
        now = time.time()
        if gc_at <= now:
            self.destroy_volume(volume_id, dry_run=dry_run)
            return True
        return False

    def delete_volume(self, volume_id):
        meta = metadata_or(volume_id)
        img_data_dir = self._get_volume_path(
            meta.get("storage_pool", config.csi_driver.default_pool), volume_id
        )
        if not img_data_dir.exists():
            return 0
        vol_img_file = img_file(volume_id)
        vol_img_size = img_size(volume_id)
        if attached_loops(vol_img_file.resolve().as_posix()):
            raise VolumeInUseError(volume_id)
        now = time.time()
        deleted_at = now
        gc_at = now
        with VolLock(volume_id):
            patch_metadata(
                volume_id,
                meta["storage_pool"],
                {"deleted_at": deleted_at, "gc_at": gc_at, "ready": False},
            )
        self.gc_if_needed(volume_id, dry_run=False)
        return vol_img_size

    def list_all_volumes(self):
        metas = glob(f"{config.csi_driver.metadata_dir}/*/disk.meta")
        return [basename(dirname(meta)) for meta in metas]

    def gc_all_volumes(self, dry_run=True):
        logger.info("Running Volume Metadata Garbage Collection", dry_run=dry_run)
        return [
            self.gc_if_needed(volume_id, dry_run=dry_run)
            for volume_id in self.list_all_volumes()
        ]

    def get_volume_stats(self, volume_id) -> VolumeStats | None:
        try:
            meta = metadata_or(volume_id)
            pool = meta.get("storage_pool", config.csi_driver.default_pool)
            thin_provision = meta.get("thin_provision", False)
            file = img_file(volume_id=volume_id)

            try:
                file_stats = stat(file)
            except FileNotFoundError:
                return None

            loop_devs = attached_loops(file.as_posix())
            if loop_devs and len(loop_devs):
                mountpoint = device_to_mountpoint(loop_devs[0])
                if mountpoint:
                    filesystem_stats = statvfs(mountpoint)
                else:
                    filesystem_stats = {"fs_usage": 0}
            else:
                filesystem_stats = {"fs_usage": 0}

            # note that "sparse" here might differ from metadata's
            # "thin_provision": if the volume was created as thick but formatted
            # with discarding, it's factually thin i.e. sparse
            return {
                "physical_size": file_stats["physical_size"],
                "logical_size": file_stats["logical_size"],
                "used": filesystem_stats["fs_usage"],
                "pool": pool,
                "sparse": (file_stats["physical_size"] < file_stats["logical_size"])
                or thin_provision,
                "thin_provision": thin_provision,
            }
        except (FileNotFoundError, KeyError):
            return None

    def get_all_volumes_stats(self) -> dict[str, VolumeStats]:
        stats = {}
        for volume_id in self.list_all_volumes():
            volume_stats = self.get_volume_stats(volume_id)
            if volume_stats:
                stats[volume_id] = self.get_volume_stats(volume_id)
        return stats

    def get_volumes_stats_by_pool(self, storage_pool: str) -> dict[str, VolumeStats]:
        stats = {}
        for volume_id in self.list_all_volumes():
            volume_stats = self.get_volume_stats(volume_id)
            if volume_stats and volume_stats["pool"] == storage_pool:
                stats[volume_id] = volume_stats
        return stats

    def migrate_metadata(self, volume_id, target_version):
        old_data = metadata_or(volume_id)
        new_data = migrate_to(old_data, target_version)
        return update_metadata(
            volume_id,
            old_data.get(
                "storage_pool",
                new_data.get("storage_pool", config.csi_driver.default_pool),
            ),
            new_data,
        )

    def migrate_metadata_dir(self):
        for old_meta in glob(
            f"{config.csi_driver.storage_pools[config.csi_driver.default_pool].path}/**/disk.meta"
        ):
            volume_id = basename(dirname(old_meta))
            for f in (
                "disk.meta",
                "disk.meta.tmp",
                "disk.lock",
            ):
                src = Path(
                    f"{config.csi_driver.storage_pools[config.csi_driver.default_pool].path}/{volume_id}/{f}"
                )
                if src.exists():
                    dst = meta_dir(volume_id) / f
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(src, dst)

    def migrate_all_volume_schemas(self):
        target_version = LATEST_SCHEMA_VERSION
        for volume_id in self.list_all_volumes():
            self.migrate_metadata(volume_id, target_version)

    def is_attached(self, volume_id):
        meta = metadata_or(volume_id)
        vol_img_dir = self._get_volume_path(meta["storage_pool"], volume_id)
        if not vol_img_dir.exists():
            return False

        vol_img_file = img_file(volume_id)
        loops = attached_loops(vol_img_file.as_posix())
        return len(loops) > 0


manager = VolumeManager()
