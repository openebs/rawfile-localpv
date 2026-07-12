import json
from pathlib import Path
import re
import warnings
from datetime import timedelta
from typing import Annotated, Final, Literal

import consts
from filesystem.types import FileSystemName
from pydantic import (
    AliasChoices,
    AnyUrl,
    BaseModel,
    ByteSize,
    DirectoryPath,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic.networks import IPvAnyAddress
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    CliSubCommand,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from utils.logs import LoggingFormats
from utils.modeltypes import ReservedCapacityMode

NAME_REGEX: Final[re.Pattern] = re.compile(
    r"^(?=.{1,253}$)(?!.*\.\.)([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)(\.([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?))*$"
)


class BaseCapability(BaseModel):
    enabled: bool


class SnapshotsCapability(BaseCapability):
    pass


class ResizeCapability(BaseCapability):
    pass


class Capabilities(BaseModel):
    resize: ResizeCapability
    snapshots: SnapshotsCapability


class StoragePool(BaseModel):
    path: DirectoryPath = Field(description="Path of the pool, Should be unique")
    reserved_capacity: (
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, pattern=r"^\d+%$"),
        ]
        | ByteSize
    ) = Field(
        default=ByteSize(0),
        description="""Reserves some disk capacity for uses other than this driver. May be specified in percentage
        of total capacity or in bytes with commonly used suffixes""",
        # since the ByteSize parses '123%', union_mode='left_to_right' and
        # annotated string coming first in the union matters
        union_mode="left_to_right",
    )

    reserved_capacity_mode: ReservedCapacityMode = Field(
        default=ReservedCapacityMode.PLAIN,
        description="""Defines reserved mode. `plain` means reserved capacity is set directly as-is;
        `subtract-from-total` means effective reserved capacity is total capacity minus reserved_capacity.
        Effectively, `subtract-from-total` is analogous to "reserve for this pool only", while "plain"
        is "reserve for everything else but this pool".""",
    )


class ExportOpenApiCmd(BaseModel):
    output: Path = Field(
        default=Path("openapi.json"),
        description="File to write the OpenAPI spec to",
    )
    indent: int = Field(default=2, description="JSON indent width")


class CSIDriverCmd(BaseModel):
    endpoint: (
        AnyUrl
        | Annotated[
            str, StringConstraints(strip_whitespace=True, pattern=r"^(.+):(.+)$")
        ]
    ) = Field(
        description="Listen address for gRPC server",
    )
    default_fs: FileSystemName = Field(
        default=FileSystemName.EXT4,
        description="Default filesystem used when creating volumes and fsType is not specified in storage class parameters",
    )
    storage_pools: dict[str, StoragePool] | None = Field(
        description="List of storage pools (Map of name to configuration), required when running node plugin",
        default=None,
    )
    default_pool: str | None = Field(
        description="Name of the default storage pool, used when no storage pool is defined in storage class",
        default=None,
    )
    internal_ip: IPvAnyAddress | None = Field(
        description="Listen ip for gRPC server (used for internal communication only)",
        default=None,
    )
    metadata_dir: DirectoryPath | None = Field(
        description="Directory to store Metadata files, required and should point to an existing path when running node plugin",
        default=None,
    )
    internal_grpc_workers: int = Field(
        description="Number of workers for the internal gRPC server",
        default=10,
    )
    nodeid: str = Field(
        validation_alias=AliasChoices("nodeid", "NODE_ID"),
        description="ID/Name of the node that is running the driver",
    )
    grpc_workers: int = Field(
        default=10, description="Number of workers for gRPC server running csi driver"
    )
    metrics_port: int = Field(
        default=9100, description="Port number of the Prometheus metrics server"
    )
    enable_metrics: bool = Field(
        default=True, description="Enables Prometheus metrics server"
    )
    plugin_type: Literal["controller", "node"] = Field(
        description="Type/Mode of the CSI plugin"
    )
    capabilities: Capabilities = Field(
        default=Capabilities(
            resize=ResizeCapability(enabled=True),
            snapshots=SnapshotsCapability(enabled=True),
        ),
        description="Controls capabilities of the CSI driver",
    )

    @field_validator("storage_pools", mode="before")
    @classmethod
    def validate_storage_pools(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception as e:
                raise ValueError(f"Invalid JSON for storage_pools: {e}")
        return v

    @model_validator(mode="after")
    def validate_node_plugin(
        self,
    ):
        if self.plugin_type == "node":
            if not self.internal_ip:
                raise ValueError(
                    "Internal Communication IP/PORT is required on node plugin"
                )
            if not self.metadata_dir:
                raise ValueError("Metadata Dir is required when running node plugin")
            if not self.storage_pools or len(self.storage_pools) == 0:
                raise ValueError(
                    "Storage Pool list is required when running node plugin"
                )

            paths = []
            for name, pool in self.storage_pools.items():
                if len(name) > 63 or len(name) < 3:
                    raise ValueError(
                        "Name of the storage pool should be between 3 and 63 characters"
                    )
                if not NAME_REGEX.match(name):
                    raise ValueError(
                        "Name of the storage pool should be DNS compatible"
                    )
                if pool.path in paths:
                    raise ValueError("Duplicate path in storage pool is not supported")
                paths.append(pool.path)
            if self.default_pool is None:
                raise ValueError("default_pool is required when running node plugin")
            if self.default_pool not in self.storage_pools:
                raise ValueError(
                    f"default_pool '{self.default_pool}' does not exist in storage_pools"
                )
        return self


class GCCmd(BaseModel):
    dry_run: bool = Field(
        description="Makes it to not change anything and just simulate GC action",
        default=True,
    )


class APICmd(BaseModel):
    host: str = Field(
        default="0.0.0.0",
        description="Host address to bind the API server",
    )
    port: int = Field(
        default=8080,
        description="Port number to bind the API server",
        gt=0,
        le=65535,
    )
    workers: int = Field(
        default=4, description="Number of uvicorn (ASGI) workers for API server"
    )


class RawFileCmd(
    BaseSettings, cli_parse_args=True, cli_exit_on_error=False, cli_kebab_case=True
):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return CliSettingsSource(settings_cls, cli_parse_args=True), env_settings

    namespace: str = Field(
        description="K8s Namespace of the driver",
    )
    log_level: Annotated[
        Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"],
        StringConstraints(strip_whitespace=True, to_upper=True),
    ] = Field(
        default="INFO",
        description="Sets log level, Set it to TRACE or DEBUG to get more information if needed",
    )
    log_format: LoggingFormats = Field(
        default=LoggingFormats.JSON,
        description="Logging format set it to pretty for a human-readable format",
    )
    ga_enabled: bool = Field(
        default=False,
        description="Enable Google Analytics metrics",
    )
    ga_id: str | None = Field(
        default=consts.GA_ID,
        description="Google Analytics project id",
    )
    ga_key: str | None = Field(
        default=consts.GA_KEY,
        description="Google Analytics project key",
    )
    ga_ping: timedelta = Field(
        default=timedelta(hours=24),
        description="Google Analytics ping interval",
    )
    node_ds: str | None = Field(
        default=None, description="Name of the node DS used for node discovery"
    )
    gc: CliSubCommand[GCCmd] = Field(
        description="Runs GC for all volumes in the node",
    )
    internal_signature: str | None = Field(
        description="Signature used for authentication of internal communication gRPC service",
        default=None,
    )
    internal_port: int | None = Field(
        description="Listen port for gRPC server (used for internal communication only)",
        default=None,
        gt=0,
        le=65535,
    )
    csi_driver: CliSubCommand[CSIDriverCmd] = Field(
        description="Starts CSI Driver",
    )
    api: CliSubCommand[APICmd] = Field(
        description="Starts API server",
    )
    export_openapi: CliSubCommand[ExportOpenApiCmd] = Field(
        description="Exports the API server's OpenAPI spec and exits",
    )

    @model_validator(mode="after")
    def validate_ds(self):
        if (self.api or self.csi_driver) and not self.node_ds:
            raise ValueError(
                "node_ds is required when running api server or csi_driver"
            )
        if (self.api or self.csi_driver) and not self.internal_signature:
            raise ValueError(
                "internal_signature is required when running api server or csi_driver"
            )
        if (self.api or self.csi_driver) and not self.internal_port:
            raise ValueError(
                "internal_port is required when running api server or csi_driver"
            )
        return self

    @model_validator(mode="after")
    def validate_ga(self):
        if self.ga_enabled and not ((self.ga_id) and (self.ga_key)):
            self.ga_enabled = False
            warnings.warn("ga_enabled is true but ga_id and ga_key are not set")
        return self
