import queue
import threading
import time

from config import config
from orchestrator.k8s import LeaderElection
from utils.logs import fmt_exception, logger

from .client import GA4Client
from .event import OpenEBSEventBuilder
from .ping import Ping
from .usage import Usage
from .version_set import VersionSet

task_queue = queue.Queue()
stop_event = threading.Event()
version_info = None


def get_usage():
    nodeid = ""
    if config.csi_driver:
        nodeid = config.csi_driver.nodeid
    global version_info
    if version_info is None:
        # If K8s API is not working correctly at the start, then there's probably
        # no point proceeding anyway
        version_info = VersionSet(nodeid)
    event_usage = Usage(
        api_secret=config.ga_key,
        measurement_id=config.ga_id,
        nodeid=nodeid,
        version_info=version_info,
    )
    return event_usage


def worker():
    logger.info("Event Worker Starting")
    # reload every 4h
    cache_duration = 60 * 60 * 4
    current_time = time.time()
    last_updated = time.time()
    event_usage = get_usage()
    while not stop_event.is_set():
        task = task_queue.get()
        if task is None:
            break

        try:
            if current_time - last_updated > cache_duration:
                event_usage.refresh()
                last_updated = current_time
                logger.trace(
                    "Updated event version info", info=event_usage.builder.__dict__
                )

            task(event_usage)
        except Exception as e:
            # todo retry?
            logger.error("Event Worker Error", exception=fmt_exception(e))
        task_queue.task_done()
    logger.info("Event Worker Exited")


def shutdown_event_worker():
    stop_event.set()


def send_event(event_fn):
    if enabled():
        task_queue.put(event_fn)


def run_event_worker():
    if enabled():
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()


def enabled() -> bool:
    return config.ga_enabled


def run_ping():
    """Run the install/ping events from the node plugins: they run on every
    node, so only the holder of the analytics lease sends them."""
    if enabled():
        election = LeaderElection("rawfile-analytics", config.csi_driver.nodeid)
        election.start()
        background_thread = threading.Thread(
            daemon=True, target=Ping(get_usage, config.ga_ping, election).run
        )
        background_thread.start()


__all__ = [
    "GA4Client",
    "OpenEBSEventBuilder",
    "Usage",
]
