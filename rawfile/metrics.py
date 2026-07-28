from config import config
from prometheus_client.core import REGISTRY
from prometheus_client.exposition import start_http_server
from prometheus_client.metrics_core import GaugeMetricFamily
from utils.devices import statvfs
from utils.storage_pool import get_capacity, reserved_capacity_handlers
from utils.volume_manager import manager as volume_manager


def get_remaining_capacity():
    val = 0
    storage_pools = getattr(getattr(config, "csi_driver", None), "storage_pools", None)
    if not storage_pools:
        return 0
    for pool in storage_pools:
        val += get_capacity(pool)
    return val


class VolumeStatsCollector:
    def __init__(self, node):
        self.node = node

    def collect(self):
        """Emit one snapshot of every rawfile metric family.

        Gauges are organised into three groups by aggregation level:

        - Node-level: a single per-node aggregate.
        - Per-pool: labelled by ``pool``, for visibility into each storage
          pool individually when multiple pools are configured.
        - Per-volume: labelled by ``volume``, for per-PVC granularity.

        """
        remaining_capacity = GaugeMetricFamily(
            "rawfile_remaining_capacity",
            "Free capacity for new volumes on this node (excluding reserved storage).",
            labels=["node"],
            unit="bytes",
        )

        pool_capacity = GaugeMetricFamily(
            "rawfile_pool_capacity",
            "Capacity allocated to the storage pool for volume provisioning "
            "(backing filesystem size minus reserved capacity).",
            labels=["node", "pool"],
            unit="bytes",
        )
        pool_backing_fs_capacity = GaugeMetricFamily(
            "rawfile_pool_backing_fs_capacity",
            "Total size of the filesystem backing the storage pool, "
            "as reported by statvfs (fs_size).",
            labels=["node", "pool"],
            unit="bytes",
        )
        pool_backing_fs_available = GaugeMetricFamily(
            "rawfile_pool_backing_fs_available",
            "Available space on the filesystem backing the storage pool, "
            "as reported by statvfs (fs_avail). Counts free space across the "
            "whole backing FS, including the rawfile-reserved slice; not just "
            "what rawfile is allowed to use.",
            labels=["node", "pool"],
            unit="bytes",
        )
        pool_backing_fs_usage = GaugeMetricFamily(
            "rawfile_pool_backing_fs_usage",
            "Used space on the filesystem backing the storage pool, "
            "as reported by statvfs (fs_size - fs_avail). Counts everything "
            "on the backing FS (rawfile-managed volumes plus non-rawfile "
            "tenants like kubelet ephemeral storage and container logs).",
            labels=["node", "pool"],
            unit="bytes",
        )
        pool_reserved = GaugeMetricFamily(
            "rawfile_pool_reserved_capacity",
            "Bytes reserved on the storage pool's backing filesystem according to its reserved_capacity configuration.",
            labels=["node", "pool"],
            unit="bytes",
        )
        pool_remaining = GaugeMetricFamily(
            "rawfile_pool_remaining_capacity",
            "Free capacity for new volumes on the storage pool (excluding reserved storage).",
            labels=["node", "pool"],
            unit="bytes",
        )
        pool_volumes_physical = GaugeMetricFamily(
            "rawfile_pool_volumes_physical",
            "Sum of physical (on-disk) sizes of all volumes in the storage pool.",
            labels=["node", "pool"],
            unit="bytes",
        )
        pool_volumes_logical = GaugeMetricFamily(
            "rawfile_pool_volumes_logical",
            "Sum of logical (provisioned) sizes of all volumes in the storage pool.",
            labels=["node", "pool"],
            unit="bytes",
        )
        pool_volume_count = GaugeMetricFamily(
            "rawfile_pool_volume_count",
            "Number of volumes provisioned on the storage pool.",
            labels=["node", "pool"],
        )
        pool_info = GaugeMetricFamily(
            "rawfile_pool_info",
            "Static information about a storage pool. Always 1; use labels for join.",
            labels=["node", "pool", "mode", "default_pool"],
        )

        volume_used = GaugeMetricFamily(
            "rawfile_volume_used",
            "Actual amount of disk used space by volume",
            labels=["node", "volume"],
            unit="bytes",
        )
        volume_total = GaugeMetricFamily(
            "rawfile_volume_total",
            "Amount of disk allocated to this volume",
            labels=["node", "volume"],
            unit="bytes",
        )
        volume_physical = GaugeMetricFamily(
            "rawfile_volume_physical",
            "Physical (on-disk) size of the volume's backing file.",
            labels=["node", "volume"],
            unit="bytes",
        )
        volume_info = GaugeMetricFamily(
            "rawfile_volume_info",
            "Static information about a volume. Always 1; use labels for join.",
            labels=["node", "volume", "pool", "sparse", "thin_provision"],
        )

        all_volumes_stats = volume_manager.get_all_volumes_stats()

        remaining_capacity.add_metric([self.node], get_remaining_capacity())
        for volume_id, stats in all_volumes_stats.items():
            volume_used.add_metric([self.node, volume_id], stats["used"])
            volume_total.add_metric([self.node, volume_id], stats["logical_size"])
            volume_physical.add_metric([self.node, volume_id], stats["physical_size"])
            volume_info.add_metric(
                [
                    self.node,
                    volume_id,
                    stats["pool"],
                    str(stats["sparse"]),
                    str(stats["thin_provision"]),
                ],
                1,
            )

        storage_pools = (
            getattr(getattr(config, "csi_driver", None), "storage_pools", None) or {}
        )
        default_pool = getattr(
            getattr(config, "csi_driver", None), "default_pool", None
        )

        for pool_name, pool in storage_pools.items():
            try:
                fs_stats = statvfs(pool.path)
            except (FileNotFoundError, OSError):
                # Pool path not yet available.
                continue

            reserved_bytes = reserved_capacity_handlers[pool.reserved_capacity_mode](
                fs_stats["fs_size"], pool.reserved_capacity
            )
            pool_capacity.add_metric(
                [self.node, pool_name], fs_stats["fs_size"] - reserved_bytes
            )
            pool_backing_fs_capacity.add_metric(
                [self.node, pool_name], fs_stats["fs_size"]
            )
            pool_backing_fs_available.add_metric(
                [self.node, pool_name], fs_stats["fs_avail"]
            )
            pool_backing_fs_usage.add_metric(
                [self.node, pool_name], fs_stats["fs_usage"]
            )
            pool_reserved.add_metric([self.node, pool_name], reserved_bytes)
            pool_remaining.add_metric([self.node, pool_name], get_capacity(pool_name))
            pool_info.add_metric(
                [
                    self.node,
                    pool_name,
                    pool.reserved_capacity_mode.value,
                    str(pool_name == default_pool),
                ],
                1,
            )

            phys_total = log_total = volume_count = 0
            for stats in all_volumes_stats.values():
                if stats.get("pool") != pool_name:
                    continue
                phys_total += stats["physical_size"]
                log_total += stats["logical_size"]
                volume_count += 1
            pool_volumes_physical.add_metric([self.node, pool_name], phys_total)
            pool_volumes_logical.add_metric([self.node, pool_name], log_total)
            pool_volume_count.add_metric([self.node, pool_name], volume_count)

        return [
            remaining_capacity,
            pool_capacity,
            pool_backing_fs_capacity,
            pool_backing_fs_available,
            pool_backing_fs_usage,
            pool_reserved,
            pool_remaining,
            pool_volumes_physical,
            pool_volumes_logical,
            pool_volume_count,
            pool_info,
            volume_used,
            volume_total,
            volume_physical,
            volume_info,
        ]


def expose_metrics(node, port):
    REGISTRY.register(VolumeStatsCollector(node))
    start_http_server(port)
