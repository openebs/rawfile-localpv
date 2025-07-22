import warnings
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    CliSubCommand,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from filesystem.types import FileSystemName
from pydantic import (
    AliasChoices,
    AnyUrl,
    BaseModel,
    ByteSize,
    StringConstraints,
    Field,
    model_validator,
)
from typing import Annotated, Literal
import consts
from utils.logs import LoggingFormats
from datetime import timedelta


class CSIDriverCmd(BaseModel):
    endpoint: (
        AnyUrl
        | Annotated[
            str, StringConstraints(strip_whitespace=True, pattern=r"^(.+):(.+)$")
        ]
    ) = Field(
        description="Listen address for gRPC server",
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


class GCCmd(BaseModel):
    dry_run: bool = Field(
        description="Makes it to not change anything and just simulate GC action",
        default=True,
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

    reserved_capacity: (
        ByteSize
        | Annotated[
            str,
            StringConstraints(strip_whitespace=True, pattern=r"^\d+%$"),
        ]
    ) = Field(
        default=ByteSize(0),
        description="Reserves capacity of data dir",
    )
    capacity_override: ByteSize | None = Field(
        default=None,
        description="Overrides total capacity of data dir",
    )
    default_fs: FileSystemName = Field(
        default=FileSystemName.EXT4,
        description="Default filesystem used where creating volumes and fsType is not specified in storage class parameters",
    )
    image_registry: str | None = Field(
        description="Registry of the image used for task pods, etc.",
        default=None,
    )
    image_repository: str = Field(
        description="Repository of the image used for task pods, etc.",
    )
    image_tag: str = Field(
        description="Image Tag of driver used for task pods, etc.",
    )
    namespace: str = Field(
        description="K8s Namespace of the driver",
    )
    node_datadir: str = Field(
        description="Data Directory path of the driver, where raw files, their matadata and their lock files are getting stored",
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
    gc: CliSubCommand[GCCmd] = Field(
        description="Runs GC for all volumes in the node",
    )
    csi_driver: CliSubCommand[CSIDriverCmd] = Field(
        description="Starts CSI Driver",
    )

    @model_validator(mode="after")
    def validate_ga(self):
        if self.ga_enabled and not ((self.ga_id) and (self.ga_key)):
            self.ga_enabled = False
            warnings.warn("ga_enabled is true but ga_id and ga_key are not set")
        return self
