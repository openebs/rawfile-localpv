#!/usr/bin/env python3
import asyncio
from concurrent import futures
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
import signal
import api_server
import bd2fs
from config.model import RawFileCmd
import grpc
import rawfile_servicer
from datetime import datetime
from csi import csi_pb2_grpc
from internal import internal_pb2_grpc
from metrics import expose_metrics
from utils import task_manager
from utils.logs import init as init_logging, logger
from internal_svc import InternalServicer, SignatureInterceptor
import consts
from analytics.ga4 import run_ping, shutdown_event_worker, run_event_worker
from orchestrator.k8s import node_ip_mapping
from utils.rawfile import is_cow_supported
from utils.remote import shutdown_grpc_channels
from utils.volume_manager import manager as volume_manager
from utils.devices import stat
from setproctitle import setproctitle
import ipaddress
import os


def __create_and_check_directory(dir: Path):
    if not dir.exists():
        logger.info("Creating directory", path=str(dir))
        dir.mkdir(parents=True, exist_ok=True)
    if not dir.is_dir():
        raise RuntimeError(f"{dir} is not a directory")
    if not os.access(dir, os.W_OK | os.R_OK | os.X_OK):
        raise RuntimeError(f"{dir} is not accessible")
    dir.chmod(consts.D_PERMS)


def node_driver_preflight_checks(task_manager: task_manager.TaskManager):
    if not config.csi_driver:
        raise RuntimeError("CSI Driver configuration is missing")
    if not config.csi_driver.metadata_dir:
        raise RuntimeError("Metadata directory is not set for node plugin")

    dirs = [
        config.csi_driver.metadata_dir,
    ]
    dirs.extend([pool.path for pool in config.csi_driver.storage_pools.values()])
    for dir in dirs:
        __create_and_check_directory(dir)

    devs = set()
    for path in [pool.path for pool in config.csi_driver.storage_pools.values()]:
        dev = stat(path)["dev"]
        if dev in devs:
            raise RuntimeError("Multiple pools cannot be backed by the same filesystem")
        devs.add(dev)

    volume_manager.migrate_metadata_dir()
    volume_manager.migrate_all_volume_schemas()
    task_manager.migrate_tasks_file_path()
    consts.COW_SUPPORT_MAP = {
        name: is_cow_supported(pool.path, pool.path)
        for name, pool in config.csi_driver.storage_pools.items()
    }


def csi_driver(config: RawFileCmd):
    driver_config = config.csi_driver
    node_ip_mapping.start()
    if not driver_config:
        raise Exception("Should run from csi driver")
    setproctitle(
        f"RawFile LocalPV CSI Driver {driver_config.plugin_type} Plugin {driver_config.nodeid}"
    )
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
    bg_task_executor = ThreadPoolExecutor(max_workers=5)
    _task_manager = task_manager.TaskManager(
        bg_task_executor,
        tasks_store_path=Path(f"{driver_config.metadata_dir}/tasks.json"),
    )
    internal_server = None
    csi_pb2_grpc.add_IdentityServicer_to_server(
        bd2fs.Bd2FsIdentityServicer(
            rawfile_servicer.RawFileIdentityServicer(),
        ),
        server,
    )
    if driver_config.plugin_type == "node":
        node_driver_preflight_checks(task_manager=_task_manager)
        csi_pb2_grpc.add_NodeServicer_to_server(
            bd2fs.Bd2FsNodeServicer(
                rawfile_servicer.RawFileNodeServicer(node_name=driver_config.nodeid),
                task_manager=_task_manager,
            ),
            server,
        )
        run_event_worker()
        internal_server = grpc.server(
            futures.ThreadPoolExecutor(
                max_workers=int(driver_config.internal_grpc_workers)
            ),
            interceptors=[SignatureInterceptor(config.internal_signature)],
        )
        internal_pb2_grpc.add_InternalServicer_to_server(
            InternalServicer(task_manager=_task_manager), internal_server
        )
        internal_ip_str = driver_config.internal_ip
        internal_ip = ipaddress.ip_address(internal_ip_str)  # type: ignore
        if internal_ip.version == 6:
            internal_ip_str = f"[{internal_ip_str}]"
        internal_server.add_insecure_port(f"{internal_ip_str}:{config.internal_port}")

    # NOTE: Controller methods are exposed on node plugin too because we are using distributed-snapshotting
    # and Snapshotting methods are only available in Controller Service right now
    csi_pb2_grpc.add_ControllerServicer_to_server(
        bd2fs.Bd2FsControllerServicer(
            rawfile_servicer.RawFileControllerServicer(task_manager=_task_manager),
            task_manager=_task_manager,
        ),
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
        if internal_server:
            internal_server.stop(grace_seconds)
        _task_manager.shutdown(grace_seconds)
        end = datetime.now()
        elapsed = end - start

        logger.info(
            "CSI Server has been stopped", elapsed=elapsed, start=start, end=end
        )
        logger.info("Stopping node plugin DS watcher")
        start = datetime.now()
        node_ip_mapping.stop()
        end = datetime.now()
        elapsed = end - start
        logger.info(
            "Node plugin DS watcher has been stopped",
            elapsed=elapsed,
            start=start,
            end=end,
        )
        logger.info("Stopping internal gRPC clients")
        if (
            config.csi_driver and config.csi_driver.plugin_type == "controller"
        ) or config.api:
            asyncio.run(shutdown_grpc_channels())
        logger.info("Internal gRPC clients stopped")

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    server.start()
    if internal_server:
        internal_server.start()
    with futures.ThreadPoolExecutor() as executor:
        terminations = [
            executor.submit(server.wait_for_termination),
        ]
        if internal_server:
            terminations.append(executor.submit(internal_server.wait_for_termination))
        futures.wait(terminations, return_when=futures.FIRST_COMPLETED)


if __name__ == "__main__":
    from config import config

    init_logging(_format=config.log_format, _level=config.log_level)
    if config.export_openapi:
        import json

        spec = api_server.app.openapi()
        config.export_openapi.output.write_text(
            json.dumps(spec, indent=config.export_openapi.indent)
        )
    elif config.gc:
        volume_manager.gc_all_volumes(config.gc.dry_run)
    elif config.csi_driver:
        if config.csi_driver.plugin_type == "node":
            volume_manager.gc_all_volumes(True)
        csi_driver(config)
    elif config.api:
        api_server.start_server(config.api.host, config.api.workers, config.api.port)
