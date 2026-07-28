from utils.logs import logger

from .client import GA4Client
from .event import OpenEBSEventBuilder
from .version_set import VersionSet


class Usage:
    def __init__(self, api_secret, measurement_id, nodeid, version_info: VersionSet):
        self.nodeid = nodeid
        self.client = GA4Client(
            decode_ga4(api_secret), decode_ga4(measurement_id), version_info.uid
        )
        self.builder = OpenEBSEventBuilder().refresh_version(version_info)

    def refresh(self):
        self.builder.refresh_version(VersionSet(self.nodeid))

    def send_install(self):
        self.builder.category("install")
        self.send()

    def send_ping(self):
        self.builder.category("rawfile-ping")
        self.send()

    def volume_provision(self, pvc_name: str, name: str, capacity: int):
        self.builder.category("volume-provision").volume_capacity(
            capacity
        ).replica_count(1).volume_claim_name(pvc_name).volume_name(name)
        self.send()

    def volume_deprovision(self, name: str, capacity: int):
        self.builder.category("volume-deprovision").volume_capacity(
            capacity
        ).replica_count(1).volume_name(name)
        self.send()

    def send(self):
        event = self.builder.build()
        if "event_category" not in event or "engine_name" not in event:
            raise ValueError(
                f"event_category and engine_name are mandatory in event={event}"
            )
        category = event["event_category"]
        engine_name = event["engine_name"]
        name = normalize(f"{engine_name}-{category}")
        self.client.send_event(name, event)

        logger.trace(f"Sent {category} Event", name=name, event=event)


def decode_ga4(b64_encoded: str) -> str:
    import base64

    decoded_bytes = base64.b64decode(b64_encoded, validate=True)
    return decoded_bytes.decode("utf-8")


def normalize(name: str) -> str:
    return name.replace("-", "_")
