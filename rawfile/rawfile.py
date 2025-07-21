#!/usr/bin/env python3
from concurrent import futures
import signal
import bd2fs
from config.model import CSIDriverCmd
import grpc
import rawfile_servicer
from datetime import datetime
from csi import csi_pb2_grpc
from metrics import expose_metrics
from utils.rawfile import gc_all_volumes, migrate_all_volume_schemas
from utils.logs import init as init_logging, logger


from analytics.ga4 import run_ping, shutdown_event_worker, run_event_worker


def csi_driver(driver_config: CSIDriverCmd):
    if driver_config.enable_metrics:
        expose_metrics(driver_config.nodeid, driver_config.metrics_port)

    if driver_config.plugin_type == "controller":
        run_ping()

    logger.debug(
        "Starting gRPC server",
        endpoint=driver_config.endpoint,
        nodeid=driver_config.nodeid,
        enable_metrics=driver_config.enable_metrics,
        plugin_type=driver_config.plugin_type,
    )
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=int(driver_config.grpc_workers))
    )
    csi_pb2_grpc.add_IdentityServicer_to_server(
        bd2fs.Bd2FsIdentityServicer(rawfile_servicer.RawFileIdentityServicer()), server
    )

    if driver_config.plugin_type == "node":
        migrate_all_volume_schemas()
        csi_pb2_grpc.add_NodeServicer_to_server(
            bd2fs.Bd2FsNodeServicer(
                rawfile_servicer.RawFileNodeServicer(node_name=driver_config.nodeid)
            ),
            server,
        )
        run_event_worker()

    # NOTE: Controller methods are exposed on node plugin too because we are using distributed-snapshotting
    # and Snapshotting methods are only available in Controller Service right now
    csi_pb2_grpc.add_ControllerServicer_to_server(
        bd2fs.Bd2FsControllerServicer(rawfile_servicer.RawFileControllerServicer()),
        server,
    )
    server.add_insecure_port(str(driver_config.endpoint))

    def signal_handler(sig, _=None):
        grace_seconds = 20

        # shutdown analytics worker
        shutdown_event_worker()

        logger.info("Received termination request", signal=signal.Signals(sig).name)
        logger.info(
            "Stopping the CSI server with a grace period", grace_seconds=grace_seconds
        )

        start = datetime.now()
        server.stop(grace_seconds)
        end = datetime.now()
        elapsed = end - start

        logger.info("CSI Server has stopped", elapsed=elapsed, start=start, end=end)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    from config import config

    init_logging(_format=config.log_format, _level=config.log_level)
    if config.gc:
        gc_all_volumes(config.gc.dry_run)
    elif config.csi_driver:
        csi_driver(config.csi_driver)
