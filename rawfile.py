#!/usr/bin/env python3
import logging
from concurrent import futures

import click
import grpc

import bd2fs
import rawfile_servicer
from consts import CONFIG
from csi import csi_pb2_grpc
from metrics import expose_metrics
from rawfile_util import migrate_all_volume_schemas, gc_all_volumes


@click.group()
@click.option("--image-repository", envvar="IMAGE_REPOSITORY")
@click.option("--image-tag", envvar="IMAGE_TAG")
@click.option("--node-datadir", envvar="NODE_DATADIR")
def cli(image_repository, image_tag, node_datadir):
    CONFIG["image_repository"] = image_repository
    CONFIG["image_tag"] = image_tag
    CONFIG["node_datadir"] = node_datadir


@cli.command()
@click.option("--endpoint", envvar="CSI_ENDPOINT", default="0.0.0.0:5000")
@click.option("--nodeid", envvar="NODE_ID")
@click.option("--enable-metrics/--disable-metrics", default=True)
def csi_driver(endpoint, nodeid, enable_metrics):
    migrate_all_volume_schemas()
    if enable_metrics:
        expose_metrics(nodeid)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    csi_pb2_grpc.add_IdentityServicer_to_server(
        bd2fs.Bd2FsIdentityServicer(rawfile_servicer.RawFileIdentityServicer()), server
    )
    csi_pb2_grpc.add_NodeServicer_to_server(
        bd2fs.Bd2FsNodeServicer(rawfile_servicer.RawFileNodeServicer(node_name=nodeid)),
        server,
    )
    csi_pb2_grpc.add_ControllerServicer_to_server(
        bd2fs.Bd2FsControllerServicer(rawfile_servicer.RawFileControllerServicer()),
        server,
    )
    server.add_insecure_port(endpoint)
    server.start()
    server.wait_for_termination()


@cli.command()
@click.option("--dry-run/--seriously", default=True)
def gc(dry_run):
    gc_all_volumes(dry_run=dry_run)


if __name__ == "__main__":
    logging.basicConfig()
    cli()
