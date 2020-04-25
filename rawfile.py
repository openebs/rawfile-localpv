#!/usr/bin/env python3
import logging
from concurrent import futures

import click
import grpc

import rawfile_servicer
from csi import csi_pb2_grpc
from metrics import expose_metrics


@click.group()
def cli():
    pass


@cli.command()
@click.option("--endpoint", envvar="CSI_ENDPOINT", default="0.0.0.0:5000")
@click.option("--nodeid", envvar="NODE_ID")
@click.option("--enable-metrics/--disable-metrics", default=True)
def csi_driver(endpoint, nodeid, enable_metrics):
    if enable_metrics:
        expose_metrics()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    csi_pb2_grpc.add_IdentityServicer_to_server(
        rawfile_servicer.RawFileIdentityServicer(), server
    )
    csi_pb2_grpc.add_NodeServicer_to_server(
        rawfile_servicer.RawFileNodeServicer(node_name=nodeid), server
    )
    csi_pb2_grpc.add_ControllerServicer_to_server(
        rawfile_servicer.RawFileControllerServicer(), server
    )
    server.add_insecure_port(endpoint)
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig()
    cli()
