from prometheus_client.core import REGISTRY
from prometheus_client.exposition import start_http_server


class VolumeStatsCollector(object):
    def collect(self):
        return []


def expose_metrics():
    REGISTRY.register(VolumeStatsCollector())
    start_http_server(9100)
