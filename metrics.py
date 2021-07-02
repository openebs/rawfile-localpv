from prometheus_client.core import REGISTRY
from prometheus_client.exposition import start_http_server
from prometheus_client.metrics_core import GaugeMetricFamily

from rawfile_util import get_capacity, get_volumes_stats


class VolumeStatsCollector(object):
    def __init__(self, node):
        self.node = node

    def collect(self):
        remaining_capacity = GaugeMetricFamily(
            "rawfile_remaining_capacity",
            "Remaining capacity for creating new volumes on this node",
            labels=["node"],
            unit="bytes",
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
        remaining_capacity.add_metric([self.node], get_capacity())
        for volume_id, stats in get_volumes_stats().items():
            volume_used.add_metric([self.node, volume_id], stats["used"])
            volume_total.add_metric([self.node, volume_id], stats["total"])
        return [remaining_capacity, volume_used, volume_total]


def expose_metrics(node):
    REGISTRY.register(VolumeStatsCollector(node))
    start_http_server(9100)
