import datetime

from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import wrappers_pb2 as _wrappers_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BlockMetadataType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[BlockMetadataType]
    FIXED_LENGTH: _ClassVar[BlockMetadataType]
    VARIABLE_LENGTH: _ClassVar[BlockMetadataType]
UNKNOWN: BlockMetadataType
FIXED_LENGTH: BlockMetadataType
VARIABLE_LENGTH: BlockMetadataType
ALPHA_ENUM_FIELD_NUMBER: _ClassVar[int]
alpha_enum: _descriptor.FieldDescriptor
ALPHA_ENUM_VALUE_FIELD_NUMBER: _ClassVar[int]
alpha_enum_value: _descriptor.FieldDescriptor
CSI_SECRET_FIELD_NUMBER: _ClassVar[int]
csi_secret: _descriptor.FieldDescriptor
ALPHA_FIELD_FIELD_NUMBER: _ClassVar[int]
alpha_field: _descriptor.FieldDescriptor
ALPHA_MESSAGE_FIELD_NUMBER: _ClassVar[int]
alpha_message: _descriptor.FieldDescriptor
ALPHA_METHOD_FIELD_NUMBER: _ClassVar[int]
alpha_method: _descriptor.FieldDescriptor
ALPHA_SERVICE_FIELD_NUMBER: _ClassVar[int]
alpha_service: _descriptor.FieldDescriptor

class GetPluginInfoRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetPluginInfoResponse(_message.Message):
    __slots__ = ("name", "vendor_version", "manifest")
    class ManifestEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    VENDOR_VERSION_FIELD_NUMBER: _ClassVar[int]
    MANIFEST_FIELD_NUMBER: _ClassVar[int]
    name: str
    vendor_version: str
    manifest: _containers.ScalarMap[str, str]
    def __init__(self, name: _Optional[str] = ..., vendor_version: _Optional[str] = ..., manifest: _Optional[_Mapping[str, str]] = ...) -> None: ...

class GetPluginCapabilitiesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetPluginCapabilitiesResponse(_message.Message):
    __slots__ = ("capabilities",)
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    capabilities: _containers.RepeatedCompositeFieldContainer[PluginCapability]
    def __init__(self, capabilities: _Optional[_Iterable[_Union[PluginCapability, _Mapping]]] = ...) -> None: ...

class PluginCapability(_message.Message):
    __slots__ = ("service", "volume_expansion")
    class Service(_message.Message):
        __slots__ = ("type",)
        class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNKNOWN: _ClassVar[PluginCapability.Service.Type]
            CONTROLLER_SERVICE: _ClassVar[PluginCapability.Service.Type]
            VOLUME_ACCESSIBILITY_CONSTRAINTS: _ClassVar[PluginCapability.Service.Type]
            GROUP_CONTROLLER_SERVICE: _ClassVar[PluginCapability.Service.Type]
            SNAPSHOT_METADATA_SERVICE: _ClassVar[PluginCapability.Service.Type]
        UNKNOWN: PluginCapability.Service.Type
        CONTROLLER_SERVICE: PluginCapability.Service.Type
        VOLUME_ACCESSIBILITY_CONSTRAINTS: PluginCapability.Service.Type
        GROUP_CONTROLLER_SERVICE: PluginCapability.Service.Type
        SNAPSHOT_METADATA_SERVICE: PluginCapability.Service.Type
        TYPE_FIELD_NUMBER: _ClassVar[int]
        type: PluginCapability.Service.Type
        def __init__(self, type: _Optional[_Union[PluginCapability.Service.Type, str]] = ...) -> None: ...
    class VolumeExpansion(_message.Message):
        __slots__ = ("type",)
        class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNKNOWN: _ClassVar[PluginCapability.VolumeExpansion.Type]
            ONLINE: _ClassVar[PluginCapability.VolumeExpansion.Type]
            OFFLINE: _ClassVar[PluginCapability.VolumeExpansion.Type]
        UNKNOWN: PluginCapability.VolumeExpansion.Type
        ONLINE: PluginCapability.VolumeExpansion.Type
        OFFLINE: PluginCapability.VolumeExpansion.Type
        TYPE_FIELD_NUMBER: _ClassVar[int]
        type: PluginCapability.VolumeExpansion.Type
        def __init__(self, type: _Optional[_Union[PluginCapability.VolumeExpansion.Type, str]] = ...) -> None: ...
    SERVICE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_EXPANSION_FIELD_NUMBER: _ClassVar[int]
    service: PluginCapability.Service
    volume_expansion: PluginCapability.VolumeExpansion
    def __init__(self, service: _Optional[_Union[PluginCapability.Service, _Mapping]] = ..., volume_expansion: _Optional[_Union[PluginCapability.VolumeExpansion, _Mapping]] = ...) -> None: ...

class ProbeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ProbeResponse(_message.Message):
    __slots__ = ("ready",)
    READY_FIELD_NUMBER: _ClassVar[int]
    ready: _wrappers_pb2.BoolValue
    def __init__(self, ready: _Optional[_Union[_wrappers_pb2.BoolValue, _Mapping]] = ...) -> None: ...

class CreateVolumeRequest(_message.Message):
    __slots__ = ("name", "capacity_range", "volume_capabilities", "parameters", "secrets", "volume_content_source", "accessibility_requirements", "mutable_parameters")
    class ParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class MutableParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_RANGE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CONTENT_SOURCE_FIELD_NUMBER: _ClassVar[int]
    ACCESSIBILITY_REQUIREMENTS_FIELD_NUMBER: _ClassVar[int]
    MUTABLE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    name: str
    capacity_range: CapacityRange
    volume_capabilities: _containers.RepeatedCompositeFieldContainer[VolumeCapability]
    parameters: _containers.ScalarMap[str, str]
    secrets: _containers.ScalarMap[str, str]
    volume_content_source: VolumeContentSource
    accessibility_requirements: TopologyRequirement
    mutable_parameters: _containers.ScalarMap[str, str]
    def __init__(self, name: _Optional[str] = ..., capacity_range: _Optional[_Union[CapacityRange, _Mapping]] = ..., volume_capabilities: _Optional[_Iterable[_Union[VolumeCapability, _Mapping]]] = ..., parameters: _Optional[_Mapping[str, str]] = ..., secrets: _Optional[_Mapping[str, str]] = ..., volume_content_source: _Optional[_Union[VolumeContentSource, _Mapping]] = ..., accessibility_requirements: _Optional[_Union[TopologyRequirement, _Mapping]] = ..., mutable_parameters: _Optional[_Mapping[str, str]] = ...) -> None: ...

class VolumeContentSource(_message.Message):
    __slots__ = ("snapshot", "volume")
    class SnapshotSource(_message.Message):
        __slots__ = ("snapshot_id",)
        SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
        snapshot_id: str
        def __init__(self, snapshot_id: _Optional[str] = ...) -> None: ...
    class VolumeSource(_message.Message):
        __slots__ = ("volume_id",)
        VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
        volume_id: str
        def __init__(self, volume_id: _Optional[str] = ...) -> None: ...
    SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    snapshot: VolumeContentSource.SnapshotSource
    volume: VolumeContentSource.VolumeSource
    def __init__(self, snapshot: _Optional[_Union[VolumeContentSource.SnapshotSource, _Mapping]] = ..., volume: _Optional[_Union[VolumeContentSource.VolumeSource, _Mapping]] = ...) -> None: ...

class CreateVolumeResponse(_message.Message):
    __slots__ = ("volume",)
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    volume: Volume
    def __init__(self, volume: _Optional[_Union[Volume, _Mapping]] = ...) -> None: ...

class VolumeCapability(_message.Message):
    __slots__ = ("block", "mount", "access_mode")
    class BlockVolume(_message.Message):
        __slots__ = ()
        def __init__(self) -> None: ...
    class MountVolume(_message.Message):
        __slots__ = ("fs_type", "mount_flags", "volume_mount_group")
        FS_TYPE_FIELD_NUMBER: _ClassVar[int]
        MOUNT_FLAGS_FIELD_NUMBER: _ClassVar[int]
        VOLUME_MOUNT_GROUP_FIELD_NUMBER: _ClassVar[int]
        fs_type: str
        mount_flags: _containers.RepeatedScalarFieldContainer[str]
        volume_mount_group: str
        def __init__(self, fs_type: _Optional[str] = ..., mount_flags: _Optional[_Iterable[str]] = ..., volume_mount_group: _Optional[str] = ...) -> None: ...
    class AccessMode(_message.Message):
        __slots__ = ("mode",)
        class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNKNOWN: _ClassVar[VolumeCapability.AccessMode.Mode]
            SINGLE_NODE_WRITER: _ClassVar[VolumeCapability.AccessMode.Mode]
            SINGLE_NODE_READER_ONLY: _ClassVar[VolumeCapability.AccessMode.Mode]
            MULTI_NODE_READER_ONLY: _ClassVar[VolumeCapability.AccessMode.Mode]
            MULTI_NODE_SINGLE_WRITER: _ClassVar[VolumeCapability.AccessMode.Mode]
            MULTI_NODE_MULTI_WRITER: _ClassVar[VolumeCapability.AccessMode.Mode]
            SINGLE_NODE_SINGLE_WRITER: _ClassVar[VolumeCapability.AccessMode.Mode]
            SINGLE_NODE_MULTI_WRITER: _ClassVar[VolumeCapability.AccessMode.Mode]
        UNKNOWN: VolumeCapability.AccessMode.Mode
        SINGLE_NODE_WRITER: VolumeCapability.AccessMode.Mode
        SINGLE_NODE_READER_ONLY: VolumeCapability.AccessMode.Mode
        MULTI_NODE_READER_ONLY: VolumeCapability.AccessMode.Mode
        MULTI_NODE_SINGLE_WRITER: VolumeCapability.AccessMode.Mode
        MULTI_NODE_MULTI_WRITER: VolumeCapability.AccessMode.Mode
        SINGLE_NODE_SINGLE_WRITER: VolumeCapability.AccessMode.Mode
        SINGLE_NODE_MULTI_WRITER: VolumeCapability.AccessMode.Mode
        MODE_FIELD_NUMBER: _ClassVar[int]
        mode: VolumeCapability.AccessMode.Mode
        def __init__(self, mode: _Optional[_Union[VolumeCapability.AccessMode.Mode, str]] = ...) -> None: ...
    BLOCK_FIELD_NUMBER: _ClassVar[int]
    MOUNT_FIELD_NUMBER: _ClassVar[int]
    ACCESS_MODE_FIELD_NUMBER: _ClassVar[int]
    block: VolumeCapability.BlockVolume
    mount: VolumeCapability.MountVolume
    access_mode: VolumeCapability.AccessMode
    def __init__(self, block: _Optional[_Union[VolumeCapability.BlockVolume, _Mapping]] = ..., mount: _Optional[_Union[VolumeCapability.MountVolume, _Mapping]] = ..., access_mode: _Optional[_Union[VolumeCapability.AccessMode, _Mapping]] = ...) -> None: ...

class CapacityRange(_message.Message):
    __slots__ = ("required_bytes", "limit_bytes")
    REQUIRED_BYTES_FIELD_NUMBER: _ClassVar[int]
    LIMIT_BYTES_FIELD_NUMBER: _ClassVar[int]
    required_bytes: int
    limit_bytes: int
    def __init__(self, required_bytes: _Optional[int] = ..., limit_bytes: _Optional[int] = ...) -> None: ...

class Volume(_message.Message):
    __slots__ = ("capacity_bytes", "volume_id", "volume_context", "content_source", "accessible_topology")
    class VolumeContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CAPACITY_BYTES_FIELD_NUMBER: _ClassVar[int]
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_SOURCE_FIELD_NUMBER: _ClassVar[int]
    ACCESSIBLE_TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    capacity_bytes: int
    volume_id: str
    volume_context: _containers.ScalarMap[str, str]
    content_source: VolumeContentSource
    accessible_topology: _containers.RepeatedCompositeFieldContainer[Topology]
    def __init__(self, capacity_bytes: _Optional[int] = ..., volume_id: _Optional[str] = ..., volume_context: _Optional[_Mapping[str, str]] = ..., content_source: _Optional[_Union[VolumeContentSource, _Mapping]] = ..., accessible_topology: _Optional[_Iterable[_Union[Topology, _Mapping]]] = ...) -> None: ...

class TopologyRequirement(_message.Message):
    __slots__ = ("requisite", "preferred")
    REQUISITE_FIELD_NUMBER: _ClassVar[int]
    PREFERRED_FIELD_NUMBER: _ClassVar[int]
    requisite: _containers.RepeatedCompositeFieldContainer[Topology]
    preferred: _containers.RepeatedCompositeFieldContainer[Topology]
    def __init__(self, requisite: _Optional[_Iterable[_Union[Topology, _Mapping]]] = ..., preferred: _Optional[_Iterable[_Union[Topology, _Mapping]]] = ...) -> None: ...

class Topology(_message.Message):
    __slots__ = ("segments",)
    class SegmentsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SEGMENTS_FIELD_NUMBER: _ClassVar[int]
    segments: _containers.ScalarMap[str, str]
    def __init__(self, segments: _Optional[_Mapping[str, str]] = ...) -> None: ...

class DeleteVolumeRequest(_message.Message):
    __slots__ = ("volume_id", "secrets")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    secrets: _containers.ScalarMap[str, str]
    def __init__(self, volume_id: _Optional[str] = ..., secrets: _Optional[_Mapping[str, str]] = ...) -> None: ...

class DeleteVolumeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ControllerPublishVolumeRequest(_message.Message):
    __slots__ = ("volume_id", "node_id", "volume_capability", "readonly", "secrets", "volume_context")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class VolumeContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CAPABILITY_FIELD_NUMBER: _ClassVar[int]
    READONLY_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    node_id: str
    volume_capability: VolumeCapability
    readonly: bool
    secrets: _containers.ScalarMap[str, str]
    volume_context: _containers.ScalarMap[str, str]
    def __init__(self, volume_id: _Optional[str] = ..., node_id: _Optional[str] = ..., volume_capability: _Optional[_Union[VolumeCapability, _Mapping]] = ..., readonly: _Optional[bool] = ..., secrets: _Optional[_Mapping[str, str]] = ..., volume_context: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ControllerPublishVolumeResponse(_message.Message):
    __slots__ = ("publish_context",)
    class PublishContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    PUBLISH_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    publish_context: _containers.ScalarMap[str, str]
    def __init__(self, publish_context: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ControllerUnpublishVolumeRequest(_message.Message):
    __slots__ = ("volume_id", "node_id", "secrets")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    node_id: str
    secrets: _containers.ScalarMap[str, str]
    def __init__(self, volume_id: _Optional[str] = ..., node_id: _Optional[str] = ..., secrets: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ControllerUnpublishVolumeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ValidateVolumeCapabilitiesRequest(_message.Message):
    __slots__ = ("volume_id", "volume_context", "volume_capabilities", "parameters", "secrets", "mutable_parameters")
    class VolumeContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class ParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class MutableParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    MUTABLE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    volume_context: _containers.ScalarMap[str, str]
    volume_capabilities: _containers.RepeatedCompositeFieldContainer[VolumeCapability]
    parameters: _containers.ScalarMap[str, str]
    secrets: _containers.ScalarMap[str, str]
    mutable_parameters: _containers.ScalarMap[str, str]
    def __init__(self, volume_id: _Optional[str] = ..., volume_context: _Optional[_Mapping[str, str]] = ..., volume_capabilities: _Optional[_Iterable[_Union[VolumeCapability, _Mapping]]] = ..., parameters: _Optional[_Mapping[str, str]] = ..., secrets: _Optional[_Mapping[str, str]] = ..., mutable_parameters: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ValidateVolumeCapabilitiesResponse(_message.Message):
    __slots__ = ("confirmed", "message")
    class Confirmed(_message.Message):
        __slots__ = ("volume_context", "volume_capabilities", "parameters", "mutable_parameters")
        class VolumeContextEntry(_message.Message):
            __slots__ = ("key", "value")
            KEY_FIELD_NUMBER: _ClassVar[int]
            VALUE_FIELD_NUMBER: _ClassVar[int]
            key: str
            value: str
            def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
        class ParametersEntry(_message.Message):
            __slots__ = ("key", "value")
            KEY_FIELD_NUMBER: _ClassVar[int]
            VALUE_FIELD_NUMBER: _ClassVar[int]
            key: str
            value: str
            def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
        class MutableParametersEntry(_message.Message):
            __slots__ = ("key", "value")
            KEY_FIELD_NUMBER: _ClassVar[int]
            VALUE_FIELD_NUMBER: _ClassVar[int]
            key: str
            value: str
            def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
        VOLUME_CONTEXT_FIELD_NUMBER: _ClassVar[int]
        VOLUME_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
        PARAMETERS_FIELD_NUMBER: _ClassVar[int]
        MUTABLE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
        volume_context: _containers.ScalarMap[str, str]
        volume_capabilities: _containers.RepeatedCompositeFieldContainer[VolumeCapability]
        parameters: _containers.ScalarMap[str, str]
        mutable_parameters: _containers.ScalarMap[str, str]
        def __init__(self, volume_context: _Optional[_Mapping[str, str]] = ..., volume_capabilities: _Optional[_Iterable[_Union[VolumeCapability, _Mapping]]] = ..., parameters: _Optional[_Mapping[str, str]] = ..., mutable_parameters: _Optional[_Mapping[str, str]] = ...) -> None: ...
    CONFIRMED_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    confirmed: ValidateVolumeCapabilitiesResponse.Confirmed
    message: str
    def __init__(self, confirmed: _Optional[_Union[ValidateVolumeCapabilitiesResponse.Confirmed, _Mapping]] = ..., message: _Optional[str] = ...) -> None: ...

class ListVolumesRequest(_message.Message):
    __slots__ = ("max_entries", "starting_token")
    MAX_ENTRIES_FIELD_NUMBER: _ClassVar[int]
    STARTING_TOKEN_FIELD_NUMBER: _ClassVar[int]
    max_entries: int
    starting_token: str
    def __init__(self, max_entries: _Optional[int] = ..., starting_token: _Optional[str] = ...) -> None: ...

class ListVolumesResponse(_message.Message):
    __slots__ = ("entries", "next_token")
    class VolumeStatus(_message.Message):
        __slots__ = ("published_node_ids", "volume_condition")
        PUBLISHED_NODE_IDS_FIELD_NUMBER: _ClassVar[int]
        VOLUME_CONDITION_FIELD_NUMBER: _ClassVar[int]
        published_node_ids: _containers.RepeatedScalarFieldContainer[str]
        volume_condition: VolumeCondition
        def __init__(self, published_node_ids: _Optional[_Iterable[str]] = ..., volume_condition: _Optional[_Union[VolumeCondition, _Mapping]] = ...) -> None: ...
    class Entry(_message.Message):
        __slots__ = ("volume", "status")
        VOLUME_FIELD_NUMBER: _ClassVar[int]
        STATUS_FIELD_NUMBER: _ClassVar[int]
        volume: Volume
        status: ListVolumesResponse.VolumeStatus
        def __init__(self, volume: _Optional[_Union[Volume, _Mapping]] = ..., status: _Optional[_Union[ListVolumesResponse.VolumeStatus, _Mapping]] = ...) -> None: ...
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    NEXT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[ListVolumesResponse.Entry]
    next_token: str
    def __init__(self, entries: _Optional[_Iterable[_Union[ListVolumesResponse.Entry, _Mapping]]] = ..., next_token: _Optional[str] = ...) -> None: ...

class ControllerGetVolumeRequest(_message.Message):
    __slots__ = ("volume_id",)
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    def __init__(self, volume_id: _Optional[str] = ...) -> None: ...

class ControllerGetVolumeResponse(_message.Message):
    __slots__ = ("volume", "status")
    class VolumeStatus(_message.Message):
        __slots__ = ("published_node_ids", "volume_condition")
        PUBLISHED_NODE_IDS_FIELD_NUMBER: _ClassVar[int]
        VOLUME_CONDITION_FIELD_NUMBER: _ClassVar[int]
        published_node_ids: _containers.RepeatedScalarFieldContainer[str]
        volume_condition: VolumeCondition
        def __init__(self, published_node_ids: _Optional[_Iterable[str]] = ..., volume_condition: _Optional[_Union[VolumeCondition, _Mapping]] = ...) -> None: ...
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    volume: Volume
    status: ControllerGetVolumeResponse.VolumeStatus
    def __init__(self, volume: _Optional[_Union[Volume, _Mapping]] = ..., status: _Optional[_Union[ControllerGetVolumeResponse.VolumeStatus, _Mapping]] = ...) -> None: ...

class ControllerModifyVolumeRequest(_message.Message):
    __slots__ = ("volume_id", "secrets", "mutable_parameters")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class MutableParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    MUTABLE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    secrets: _containers.ScalarMap[str, str]
    mutable_parameters: _containers.ScalarMap[str, str]
    def __init__(self, volume_id: _Optional[str] = ..., secrets: _Optional[_Mapping[str, str]] = ..., mutable_parameters: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ControllerModifyVolumeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetCapacityRequest(_message.Message):
    __slots__ = ("volume_capabilities", "parameters", "accessible_topology")
    class ParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VOLUME_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    ACCESSIBLE_TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    volume_capabilities: _containers.RepeatedCompositeFieldContainer[VolumeCapability]
    parameters: _containers.ScalarMap[str, str]
    accessible_topology: Topology
    def __init__(self, volume_capabilities: _Optional[_Iterable[_Union[VolumeCapability, _Mapping]]] = ..., parameters: _Optional[_Mapping[str, str]] = ..., accessible_topology: _Optional[_Union[Topology, _Mapping]] = ...) -> None: ...

class GetCapacityResponse(_message.Message):
    __slots__ = ("available_capacity", "maximum_volume_size", "minimum_volume_size")
    AVAILABLE_CAPACITY_FIELD_NUMBER: _ClassVar[int]
    MAXIMUM_VOLUME_SIZE_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_VOLUME_SIZE_FIELD_NUMBER: _ClassVar[int]
    available_capacity: int
    maximum_volume_size: _wrappers_pb2.Int64Value
    minimum_volume_size: _wrappers_pb2.Int64Value
    def __init__(self, available_capacity: _Optional[int] = ..., maximum_volume_size: _Optional[_Union[_wrappers_pb2.Int64Value, _Mapping]] = ..., minimum_volume_size: _Optional[_Union[_wrappers_pb2.Int64Value, _Mapping]] = ...) -> None: ...

class ControllerGetCapabilitiesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ControllerGetCapabilitiesResponse(_message.Message):
    __slots__ = ("capabilities",)
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    capabilities: _containers.RepeatedCompositeFieldContainer[ControllerServiceCapability]
    def __init__(self, capabilities: _Optional[_Iterable[_Union[ControllerServiceCapability, _Mapping]]] = ...) -> None: ...

class ControllerServiceCapability(_message.Message):
    __slots__ = ("rpc",)
    class RPC(_message.Message):
        __slots__ = ("type",)
        class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNKNOWN: _ClassVar[ControllerServiceCapability.RPC.Type]
            CREATE_DELETE_VOLUME: _ClassVar[ControllerServiceCapability.RPC.Type]
            PUBLISH_UNPUBLISH_VOLUME: _ClassVar[ControllerServiceCapability.RPC.Type]
            LIST_VOLUMES: _ClassVar[ControllerServiceCapability.RPC.Type]
            GET_CAPACITY: _ClassVar[ControllerServiceCapability.RPC.Type]
            CREATE_DELETE_SNAPSHOT: _ClassVar[ControllerServiceCapability.RPC.Type]
            LIST_SNAPSHOTS: _ClassVar[ControllerServiceCapability.RPC.Type]
            CLONE_VOLUME: _ClassVar[ControllerServiceCapability.RPC.Type]
            PUBLISH_READONLY: _ClassVar[ControllerServiceCapability.RPC.Type]
            EXPAND_VOLUME: _ClassVar[ControllerServiceCapability.RPC.Type]
            LIST_VOLUMES_PUBLISHED_NODES: _ClassVar[ControllerServiceCapability.RPC.Type]
            VOLUME_CONDITION: _ClassVar[ControllerServiceCapability.RPC.Type]
            GET_VOLUME: _ClassVar[ControllerServiceCapability.RPC.Type]
            SINGLE_NODE_MULTI_WRITER: _ClassVar[ControllerServiceCapability.RPC.Type]
            MODIFY_VOLUME: _ClassVar[ControllerServiceCapability.RPC.Type]
        UNKNOWN: ControllerServiceCapability.RPC.Type
        CREATE_DELETE_VOLUME: ControllerServiceCapability.RPC.Type
        PUBLISH_UNPUBLISH_VOLUME: ControllerServiceCapability.RPC.Type
        LIST_VOLUMES: ControllerServiceCapability.RPC.Type
        GET_CAPACITY: ControllerServiceCapability.RPC.Type
        CREATE_DELETE_SNAPSHOT: ControllerServiceCapability.RPC.Type
        LIST_SNAPSHOTS: ControllerServiceCapability.RPC.Type
        CLONE_VOLUME: ControllerServiceCapability.RPC.Type
        PUBLISH_READONLY: ControllerServiceCapability.RPC.Type
        EXPAND_VOLUME: ControllerServiceCapability.RPC.Type
        LIST_VOLUMES_PUBLISHED_NODES: ControllerServiceCapability.RPC.Type
        VOLUME_CONDITION: ControllerServiceCapability.RPC.Type
        GET_VOLUME: ControllerServiceCapability.RPC.Type
        SINGLE_NODE_MULTI_WRITER: ControllerServiceCapability.RPC.Type
        MODIFY_VOLUME: ControllerServiceCapability.RPC.Type
        TYPE_FIELD_NUMBER: _ClassVar[int]
        type: ControllerServiceCapability.RPC.Type
        def __init__(self, type: _Optional[_Union[ControllerServiceCapability.RPC.Type, str]] = ...) -> None: ...
    RPC_FIELD_NUMBER: _ClassVar[int]
    rpc: ControllerServiceCapability.RPC
    def __init__(self, rpc: _Optional[_Union[ControllerServiceCapability.RPC, _Mapping]] = ...) -> None: ...

class CreateSnapshotRequest(_message.Message):
    __slots__ = ("source_volume_id", "name", "secrets", "parameters")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class ParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SOURCE_VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    source_volume_id: str
    name: str
    secrets: _containers.ScalarMap[str, str]
    parameters: _containers.ScalarMap[str, str]
    def __init__(self, source_volume_id: _Optional[str] = ..., name: _Optional[str] = ..., secrets: _Optional[_Mapping[str, str]] = ..., parameters: _Optional[_Mapping[str, str]] = ...) -> None: ...

class CreateSnapshotResponse(_message.Message):
    __slots__ = ("snapshot",)
    SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
    snapshot: Snapshot
    def __init__(self, snapshot: _Optional[_Union[Snapshot, _Mapping]] = ...) -> None: ...

class Snapshot(_message.Message):
    __slots__ = ("size_bytes", "snapshot_id", "source_volume_id", "creation_time", "ready_to_use", "group_snapshot_id")
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    CREATION_TIME_FIELD_NUMBER: _ClassVar[int]
    READY_TO_USE_FIELD_NUMBER: _ClassVar[int]
    GROUP_SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    size_bytes: int
    snapshot_id: str
    source_volume_id: str
    creation_time: _timestamp_pb2.Timestamp
    ready_to_use: bool
    group_snapshot_id: str
    def __init__(self, size_bytes: _Optional[int] = ..., snapshot_id: _Optional[str] = ..., source_volume_id: _Optional[str] = ..., creation_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., ready_to_use: _Optional[bool] = ..., group_snapshot_id: _Optional[str] = ...) -> None: ...

class DeleteSnapshotRequest(_message.Message):
    __slots__ = ("snapshot_id", "secrets")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    snapshot_id: str
    secrets: _containers.ScalarMap[str, str]
    def __init__(self, snapshot_id: _Optional[str] = ..., secrets: _Optional[_Mapping[str, str]] = ...) -> None: ...

class DeleteSnapshotResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListSnapshotsRequest(_message.Message):
    __slots__ = ("max_entries", "starting_token", "source_volume_id", "snapshot_id", "secrets")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    MAX_ENTRIES_FIELD_NUMBER: _ClassVar[int]
    STARTING_TOKEN_FIELD_NUMBER: _ClassVar[int]
    SOURCE_VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    max_entries: int
    starting_token: str
    source_volume_id: str
    snapshot_id: str
    secrets: _containers.ScalarMap[str, str]
    def __init__(self, max_entries: _Optional[int] = ..., starting_token: _Optional[str] = ..., source_volume_id: _Optional[str] = ..., snapshot_id: _Optional[str] = ..., secrets: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ListSnapshotsResponse(_message.Message):
    __slots__ = ("entries", "next_token")
    class Entry(_message.Message):
        __slots__ = ("snapshot",)
        SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
        snapshot: Snapshot
        def __init__(self, snapshot: _Optional[_Union[Snapshot, _Mapping]] = ...) -> None: ...
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    NEXT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[ListSnapshotsResponse.Entry]
    next_token: str
    def __init__(self, entries: _Optional[_Iterable[_Union[ListSnapshotsResponse.Entry, _Mapping]]] = ..., next_token: _Optional[str] = ...) -> None: ...

class ControllerExpandVolumeRequest(_message.Message):
    __slots__ = ("volume_id", "capacity_range", "secrets", "volume_capability")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_RANGE_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CAPABILITY_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    capacity_range: CapacityRange
    secrets: _containers.ScalarMap[str, str]
    volume_capability: VolumeCapability
    def __init__(self, volume_id: _Optional[str] = ..., capacity_range: _Optional[_Union[CapacityRange, _Mapping]] = ..., secrets: _Optional[_Mapping[str, str]] = ..., volume_capability: _Optional[_Union[VolumeCapability, _Mapping]] = ...) -> None: ...

class ControllerExpandVolumeResponse(_message.Message):
    __slots__ = ("capacity_bytes", "node_expansion_required")
    CAPACITY_BYTES_FIELD_NUMBER: _ClassVar[int]
    NODE_EXPANSION_REQUIRED_FIELD_NUMBER: _ClassVar[int]
    capacity_bytes: int
    node_expansion_required: bool
    def __init__(self, capacity_bytes: _Optional[int] = ..., node_expansion_required: _Optional[bool] = ...) -> None: ...

class NodeStageVolumeRequest(_message.Message):
    __slots__ = ("volume_id", "publish_context", "staging_target_path", "volume_capability", "secrets", "volume_context")
    class PublishContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class VolumeContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    PUBLISH_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    STAGING_TARGET_PATH_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CAPABILITY_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    publish_context: _containers.ScalarMap[str, str]
    staging_target_path: str
    volume_capability: VolumeCapability
    secrets: _containers.ScalarMap[str, str]
    volume_context: _containers.ScalarMap[str, str]
    def __init__(self, volume_id: _Optional[str] = ..., publish_context: _Optional[_Mapping[str, str]] = ..., staging_target_path: _Optional[str] = ..., volume_capability: _Optional[_Union[VolumeCapability, _Mapping]] = ..., secrets: _Optional[_Mapping[str, str]] = ..., volume_context: _Optional[_Mapping[str, str]] = ...) -> None: ...

class NodeStageVolumeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class NodeUnstageVolumeRequest(_message.Message):
    __slots__ = ("volume_id", "staging_target_path")
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    STAGING_TARGET_PATH_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    staging_target_path: str
    def __init__(self, volume_id: _Optional[str] = ..., staging_target_path: _Optional[str] = ...) -> None: ...

class NodeUnstageVolumeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class NodePublishVolumeRequest(_message.Message):
    __slots__ = ("volume_id", "publish_context", "staging_target_path", "target_path", "volume_capability", "readonly", "secrets", "volume_context")
    class PublishContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class VolumeContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    PUBLISH_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    STAGING_TARGET_PATH_FIELD_NUMBER: _ClassVar[int]
    TARGET_PATH_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CAPABILITY_FIELD_NUMBER: _ClassVar[int]
    READONLY_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    publish_context: _containers.ScalarMap[str, str]
    staging_target_path: str
    target_path: str
    volume_capability: VolumeCapability
    readonly: bool
    secrets: _containers.ScalarMap[str, str]
    volume_context: _containers.ScalarMap[str, str]
    def __init__(self, volume_id: _Optional[str] = ..., publish_context: _Optional[_Mapping[str, str]] = ..., staging_target_path: _Optional[str] = ..., target_path: _Optional[str] = ..., volume_capability: _Optional[_Union[VolumeCapability, _Mapping]] = ..., readonly: _Optional[bool] = ..., secrets: _Optional[_Mapping[str, str]] = ..., volume_context: _Optional[_Mapping[str, str]] = ...) -> None: ...

class NodePublishVolumeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class NodeUnpublishVolumeRequest(_message.Message):
    __slots__ = ("volume_id", "target_path")
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    TARGET_PATH_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    target_path: str
    def __init__(self, volume_id: _Optional[str] = ..., target_path: _Optional[str] = ...) -> None: ...

class NodeUnpublishVolumeResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class NodeGetVolumeStatsRequest(_message.Message):
    __slots__ = ("volume_id", "volume_path", "staging_target_path")
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    VOLUME_PATH_FIELD_NUMBER: _ClassVar[int]
    STAGING_TARGET_PATH_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    volume_path: str
    staging_target_path: str
    def __init__(self, volume_id: _Optional[str] = ..., volume_path: _Optional[str] = ..., staging_target_path: _Optional[str] = ...) -> None: ...

class NodeGetVolumeStatsResponse(_message.Message):
    __slots__ = ("usage", "volume_condition")
    USAGE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CONDITION_FIELD_NUMBER: _ClassVar[int]
    usage: _containers.RepeatedCompositeFieldContainer[VolumeUsage]
    volume_condition: VolumeCondition
    def __init__(self, usage: _Optional[_Iterable[_Union[VolumeUsage, _Mapping]]] = ..., volume_condition: _Optional[_Union[VolumeCondition, _Mapping]] = ...) -> None: ...

class VolumeUsage(_message.Message):
    __slots__ = ("available", "total", "used", "unit")
    class Unit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[VolumeUsage.Unit]
        BYTES: _ClassVar[VolumeUsage.Unit]
        INODES: _ClassVar[VolumeUsage.Unit]
    UNKNOWN: VolumeUsage.Unit
    BYTES: VolumeUsage.Unit
    INODES: VolumeUsage.Unit
    AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    USED_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    available: int
    total: int
    used: int
    unit: VolumeUsage.Unit
    def __init__(self, available: _Optional[int] = ..., total: _Optional[int] = ..., used: _Optional[int] = ..., unit: _Optional[_Union[VolumeUsage.Unit, str]] = ...) -> None: ...

class VolumeCondition(_message.Message):
    __slots__ = ("abnormal", "message")
    ABNORMAL_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    abnormal: bool
    message: str
    def __init__(self, abnormal: _Optional[bool] = ..., message: _Optional[str] = ...) -> None: ...

class NodeGetCapabilitiesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class NodeGetCapabilitiesResponse(_message.Message):
    __slots__ = ("capabilities",)
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    capabilities: _containers.RepeatedCompositeFieldContainer[NodeServiceCapability]
    def __init__(self, capabilities: _Optional[_Iterable[_Union[NodeServiceCapability, _Mapping]]] = ...) -> None: ...

class NodeServiceCapability(_message.Message):
    __slots__ = ("rpc",)
    class RPC(_message.Message):
        __slots__ = ("type",)
        class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNKNOWN: _ClassVar[NodeServiceCapability.RPC.Type]
            STAGE_UNSTAGE_VOLUME: _ClassVar[NodeServiceCapability.RPC.Type]
            GET_VOLUME_STATS: _ClassVar[NodeServiceCapability.RPC.Type]
            EXPAND_VOLUME: _ClassVar[NodeServiceCapability.RPC.Type]
            VOLUME_CONDITION: _ClassVar[NodeServiceCapability.RPC.Type]
            SINGLE_NODE_MULTI_WRITER: _ClassVar[NodeServiceCapability.RPC.Type]
            VOLUME_MOUNT_GROUP: _ClassVar[NodeServiceCapability.RPC.Type]
        UNKNOWN: NodeServiceCapability.RPC.Type
        STAGE_UNSTAGE_VOLUME: NodeServiceCapability.RPC.Type
        GET_VOLUME_STATS: NodeServiceCapability.RPC.Type
        EXPAND_VOLUME: NodeServiceCapability.RPC.Type
        VOLUME_CONDITION: NodeServiceCapability.RPC.Type
        SINGLE_NODE_MULTI_WRITER: NodeServiceCapability.RPC.Type
        VOLUME_MOUNT_GROUP: NodeServiceCapability.RPC.Type
        TYPE_FIELD_NUMBER: _ClassVar[int]
        type: NodeServiceCapability.RPC.Type
        def __init__(self, type: _Optional[_Union[NodeServiceCapability.RPC.Type, str]] = ...) -> None: ...
    RPC_FIELD_NUMBER: _ClassVar[int]
    rpc: NodeServiceCapability.RPC
    def __init__(self, rpc: _Optional[_Union[NodeServiceCapability.RPC, _Mapping]] = ...) -> None: ...

class NodeGetInfoRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class NodeGetInfoResponse(_message.Message):
    __slots__ = ("node_id", "max_volumes_per_node", "accessible_topology")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    MAX_VOLUMES_PER_NODE_FIELD_NUMBER: _ClassVar[int]
    ACCESSIBLE_TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    max_volumes_per_node: int
    accessible_topology: Topology
    def __init__(self, node_id: _Optional[str] = ..., max_volumes_per_node: _Optional[int] = ..., accessible_topology: _Optional[_Union[Topology, _Mapping]] = ...) -> None: ...

class NodeExpandVolumeRequest(_message.Message):
    __slots__ = ("volume_id", "volume_path", "capacity_range", "staging_target_path", "volume_capability", "secrets")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    VOLUME_PATH_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_RANGE_FIELD_NUMBER: _ClassVar[int]
    STAGING_TARGET_PATH_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CAPABILITY_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    volume_path: str
    capacity_range: CapacityRange
    staging_target_path: str
    volume_capability: VolumeCapability
    secrets: _containers.ScalarMap[str, str]
    def __init__(self, volume_id: _Optional[str] = ..., volume_path: _Optional[str] = ..., capacity_range: _Optional[_Union[CapacityRange, _Mapping]] = ..., staging_target_path: _Optional[str] = ..., volume_capability: _Optional[_Union[VolumeCapability, _Mapping]] = ..., secrets: _Optional[_Mapping[str, str]] = ...) -> None: ...

class NodeExpandVolumeResponse(_message.Message):
    __slots__ = ("capacity_bytes",)
    CAPACITY_BYTES_FIELD_NUMBER: _ClassVar[int]
    capacity_bytes: int
    def __init__(self, capacity_bytes: _Optional[int] = ...) -> None: ...

class GroupControllerGetCapabilitiesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GroupControllerGetCapabilitiesResponse(_message.Message):
    __slots__ = ("capabilities",)
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    capabilities: _containers.RepeatedCompositeFieldContainer[GroupControllerServiceCapability]
    def __init__(self, capabilities: _Optional[_Iterable[_Union[GroupControllerServiceCapability, _Mapping]]] = ...) -> None: ...

class GroupControllerServiceCapability(_message.Message):
    __slots__ = ("rpc",)
    class RPC(_message.Message):
        __slots__ = ("type",)
        class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNKNOWN: _ClassVar[GroupControllerServiceCapability.RPC.Type]
            CREATE_DELETE_GET_VOLUME_GROUP_SNAPSHOT: _ClassVar[GroupControllerServiceCapability.RPC.Type]
        UNKNOWN: GroupControllerServiceCapability.RPC.Type
        CREATE_DELETE_GET_VOLUME_GROUP_SNAPSHOT: GroupControllerServiceCapability.RPC.Type
        TYPE_FIELD_NUMBER: _ClassVar[int]
        type: GroupControllerServiceCapability.RPC.Type
        def __init__(self, type: _Optional[_Union[GroupControllerServiceCapability.RPC.Type, str]] = ...) -> None: ...
    RPC_FIELD_NUMBER: _ClassVar[int]
    rpc: GroupControllerServiceCapability.RPC
    def __init__(self, rpc: _Optional[_Union[GroupControllerServiceCapability.RPC, _Mapping]] = ...) -> None: ...

class CreateVolumeGroupSnapshotRequest(_message.Message):
    __slots__ = ("name", "source_volume_ids", "secrets", "parameters")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class ParametersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    SOURCE_VOLUME_IDS_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    name: str
    source_volume_ids: _containers.RepeatedScalarFieldContainer[str]
    secrets: _containers.ScalarMap[str, str]
    parameters: _containers.ScalarMap[str, str]
    def __init__(self, name: _Optional[str] = ..., source_volume_ids: _Optional[_Iterable[str]] = ..., secrets: _Optional[_Mapping[str, str]] = ..., parameters: _Optional[_Mapping[str, str]] = ...) -> None: ...

class CreateVolumeGroupSnapshotResponse(_message.Message):
    __slots__ = ("group_snapshot",)
    GROUP_SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
    group_snapshot: VolumeGroupSnapshot
    def __init__(self, group_snapshot: _Optional[_Union[VolumeGroupSnapshot, _Mapping]] = ...) -> None: ...

class VolumeGroupSnapshot(_message.Message):
    __slots__ = ("group_snapshot_id", "snapshots", "creation_time", "ready_to_use")
    GROUP_SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOTS_FIELD_NUMBER: _ClassVar[int]
    CREATION_TIME_FIELD_NUMBER: _ClassVar[int]
    READY_TO_USE_FIELD_NUMBER: _ClassVar[int]
    group_snapshot_id: str
    snapshots: _containers.RepeatedCompositeFieldContainer[Snapshot]
    creation_time: _timestamp_pb2.Timestamp
    ready_to_use: bool
    def __init__(self, group_snapshot_id: _Optional[str] = ..., snapshots: _Optional[_Iterable[_Union[Snapshot, _Mapping]]] = ..., creation_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., ready_to_use: _Optional[bool] = ...) -> None: ...

class DeleteVolumeGroupSnapshotRequest(_message.Message):
    __slots__ = ("group_snapshot_id", "snapshot_ids", "secrets")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    GROUP_SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_IDS_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    group_snapshot_id: str
    snapshot_ids: _containers.RepeatedScalarFieldContainer[str]
    secrets: _containers.ScalarMap[str, str]
    def __init__(self, group_snapshot_id: _Optional[str] = ..., snapshot_ids: _Optional[_Iterable[str]] = ..., secrets: _Optional[_Mapping[str, str]] = ...) -> None: ...

class DeleteVolumeGroupSnapshotResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetVolumeGroupSnapshotRequest(_message.Message):
    __slots__ = ("group_snapshot_id", "snapshot_ids", "secrets")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    GROUP_SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_IDS_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    group_snapshot_id: str
    snapshot_ids: _containers.RepeatedScalarFieldContainer[str]
    secrets: _containers.ScalarMap[str, str]
    def __init__(self, group_snapshot_id: _Optional[str] = ..., snapshot_ids: _Optional[_Iterable[str]] = ..., secrets: _Optional[_Mapping[str, str]] = ...) -> None: ...

class GetVolumeGroupSnapshotResponse(_message.Message):
    __slots__ = ("group_snapshot",)
    GROUP_SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
    group_snapshot: VolumeGroupSnapshot
    def __init__(self, group_snapshot: _Optional[_Union[VolumeGroupSnapshot, _Mapping]] = ...) -> None: ...

class BlockMetadata(_message.Message):
    __slots__ = ("byte_offset", "size_bytes")
    BYTE_OFFSET_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    byte_offset: int
    size_bytes: int
    def __init__(self, byte_offset: _Optional[int] = ..., size_bytes: _Optional[int] = ...) -> None: ...

class GetMetadataAllocatedRequest(_message.Message):
    __slots__ = ("snapshot_id", "starting_offset", "max_results", "secrets")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    STARTING_OFFSET_FIELD_NUMBER: _ClassVar[int]
    MAX_RESULTS_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    snapshot_id: str
    starting_offset: int
    max_results: int
    secrets: _containers.ScalarMap[str, str]
    def __init__(self, snapshot_id: _Optional[str] = ..., starting_offset: _Optional[int] = ..., max_results: _Optional[int] = ..., secrets: _Optional[_Mapping[str, str]] = ...) -> None: ...

class GetMetadataAllocatedResponse(_message.Message):
    __slots__ = ("block_metadata_type", "volume_capacity_bytes", "block_metadata")
    BLOCK_METADATA_TYPE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CAPACITY_BYTES_FIELD_NUMBER: _ClassVar[int]
    BLOCK_METADATA_FIELD_NUMBER: _ClassVar[int]
    block_metadata_type: BlockMetadataType
    volume_capacity_bytes: int
    block_metadata: _containers.RepeatedCompositeFieldContainer[BlockMetadata]
    def __init__(self, block_metadata_type: _Optional[_Union[BlockMetadataType, str]] = ..., volume_capacity_bytes: _Optional[int] = ..., block_metadata: _Optional[_Iterable[_Union[BlockMetadata, _Mapping]]] = ...) -> None: ...

class GetMetadataDeltaRequest(_message.Message):
    __slots__ = ("base_snapshot_id", "target_snapshot_id", "starting_offset", "max_results", "secrets")
    class SecretsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    BASE_SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    TARGET_SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    STARTING_OFFSET_FIELD_NUMBER: _ClassVar[int]
    MAX_RESULTS_FIELD_NUMBER: _ClassVar[int]
    SECRETS_FIELD_NUMBER: _ClassVar[int]
    base_snapshot_id: str
    target_snapshot_id: str
    starting_offset: int
    max_results: int
    secrets: _containers.ScalarMap[str, str]
    def __init__(self, base_snapshot_id: _Optional[str] = ..., target_snapshot_id: _Optional[str] = ..., starting_offset: _Optional[int] = ..., max_results: _Optional[int] = ..., secrets: _Optional[_Mapping[str, str]] = ...) -> None: ...

class GetMetadataDeltaResponse(_message.Message):
    __slots__ = ("block_metadata_type", "volume_capacity_bytes", "block_metadata")
    BLOCK_METADATA_TYPE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_CAPACITY_BYTES_FIELD_NUMBER: _ClassVar[int]
    BLOCK_METADATA_FIELD_NUMBER: _ClassVar[int]
    block_metadata_type: BlockMetadataType
    volume_capacity_bytes: int
    block_metadata: _containers.RepeatedCompositeFieldContainer[BlockMetadata]
    def __init__(self, block_metadata_type: _Optional[_Union[BlockMetadataType, str]] = ..., volume_capacity_bytes: _Optional[int] = ..., block_metadata: _Optional[_Iterable[_Union[BlockMetadata, _Mapping]]] = ...) -> None: ...
