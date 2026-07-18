from google.protobuf import any_pb2 as _any_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ExpandRawFileStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OK: _ClassVar[ExpandRawFileStatus]
    RESOURCE_EXHAUSTED: _ClassVar[ExpandRawFileStatus]
OK: ExpandRawFileStatus
RESOURCE_EXHAUSTED: ExpandRawFileStatus

class ExpandRawFileRequest(_message.Message):
    __slots__ = ("volume_id", "new_size")
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_SIZE_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    new_size: int
    def __init__(self, volume_id: _Optional[str] = ..., new_size: _Optional[int] = ...) -> None: ...

class ExpandRawFileResponse(_message.Message):
    __slots__ = ("is_attached", "status")
    IS_ATTACHED_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    is_attached: bool
    status: ExpandRawFileStatus
    def __init__(self, is_attached: _Optional[bool] = ..., status: _Optional[_Union[ExpandRawFileStatus, str]] = ...) -> None: ...

class GetRawFileRequest(_message.Message):
    __slots__ = ("volume_id", "with_data", "snapshot_id")
    VOLUME_ID_FIELD_NUMBER: _ClassVar[int]
    WITH_DATA_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    volume_id: str
    with_data: bool
    snapshot_id: str
    def __init__(self, volume_id: _Optional[str] = ..., with_data: _Optional[bool] = ..., snapshot_id: _Optional[str] = ...) -> None: ...

class GetRawFileResponse(_message.Message):
    __slots__ = ("metadata", "data")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _any_pb2.Any
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_any_pb2.Any, _Mapping]] = ...) -> None: ...
    METADATA_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    metadata: _containers.MessageMap[str, _any_pb2.Any]
    data: bytes
    def __init__(self, metadata: _Optional[_Mapping[str, _any_pb2.Any]] = ..., data: _Optional[bytes] = ...) -> None: ...

class GetPoolsStatsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PoolStat(_message.Message):
    __slots__ = ("reserved_capacity", "path", "reserved_capacity_mode", "capacity", "copy_on_write_supported")
    RESERVED_CAPACITY_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    RESERVED_CAPACITY_MODE_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    COPY_ON_WRITE_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
    reserved_capacity: str
    path: str
    reserved_capacity_mode: str
    capacity: int
    copy_on_write_supported: bool
    def __init__(self, reserved_capacity: _Optional[str] = ..., path: _Optional[str] = ..., reserved_capacity_mode: _Optional[str] = ..., capacity: _Optional[int] = ..., copy_on_write_supported: _Optional[bool] = ...) -> None: ...

class GetPoolsStatsResponse(_message.Message):
    __slots__ = ("stats",)
    class StatsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: PoolStat
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[PoolStat, _Mapping]] = ...) -> None: ...
    STATS_FIELD_NUMBER: _ClassVar[int]
    stats: _containers.MessageMap[str, PoolStat]
    def __init__(self, stats: _Optional[_Mapping[str, PoolStat]] = ...) -> None: ...

class VolumeStat(_message.Message):
    __slots__ = ("name", "size", "copy_on_write", "thin_provision", "ready", "deleted_at", "created_at", "gc_at", "storage_pool", "freezefs", "img_file", "physical_size", "logical_size", "used")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    COPY_ON_WRITE_FIELD_NUMBER: _ClassVar[int]
    THIN_PROVISION_FIELD_NUMBER: _ClassVar[int]
    READY_FIELD_NUMBER: _ClassVar[int]
    DELETED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    GC_AT_FIELD_NUMBER: _ClassVar[int]
    STORAGE_POOL_FIELD_NUMBER: _ClassVar[int]
    FREEZEFS_FIELD_NUMBER: _ClassVar[int]
    IMG_FILE_FIELD_NUMBER: _ClassVar[int]
    PHYSICAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    LOGICAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    USED_FIELD_NUMBER: _ClassVar[int]
    name: str
    size: int
    copy_on_write: bool
    thin_provision: bool
    ready: bool
    deleted_at: float
    created_at: float
    gc_at: float
    storage_pool: str
    freezefs: bool
    img_file: str
    physical_size: int
    logical_size: int
    used: int
    def __init__(self, name: _Optional[str] = ..., size: _Optional[int] = ..., copy_on_write: _Optional[bool] = ..., thin_provision: _Optional[bool] = ..., ready: _Optional[bool] = ..., deleted_at: _Optional[float] = ..., created_at: _Optional[float] = ..., gc_at: _Optional[float] = ..., storage_pool: _Optional[str] = ..., freezefs: _Optional[bool] = ..., img_file: _Optional[str] = ..., physical_size: _Optional[int] = ..., logical_size: _Optional[int] = ..., used: _Optional[int] = ...) -> None: ...

class GetVolumesStatRequest(_message.Message):
    __slots__ = ("pool_name", "volume_name")
    POOL_NAME_FIELD_NUMBER: _ClassVar[int]
    VOLUME_NAME_FIELD_NUMBER: _ClassVar[int]
    pool_name: str
    volume_name: str
    def __init__(self, pool_name: _Optional[str] = ..., volume_name: _Optional[str] = ...) -> None: ...

class GetVolumesStatResponse(_message.Message):
    __slots__ = ("stats",)
    class StatsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: VolumeStat
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[VolumeStat, _Mapping]] = ...) -> None: ...
    STATS_FIELD_NUMBER: _ClassVar[int]
    stats: _containers.MessageMap[str, VolumeStat]
    def __init__(self, stats: _Optional[_Mapping[str, VolumeStat]] = ...) -> None: ...

class GetNodeTasksRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Task(_message.Message):
    __slots__ = ("task", "args", "kwargs", "retry_count", "state")
    class KwargsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _any_pb2.Any
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_any_pb2.Any, _Mapping]] = ...) -> None: ...
    TASK_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    KWARGS_FIELD_NUMBER: _ClassVar[int]
    RETRY_COUNT_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    task: str
    args: _containers.RepeatedScalarFieldContainer[str]
    kwargs: _containers.MessageMap[str, _any_pb2.Any]
    retry_count: int
    state: str
    def __init__(self, task: _Optional[str] = ..., args: _Optional[_Iterable[str]] = ..., kwargs: _Optional[_Mapping[str, _any_pb2.Any]] = ..., retry_count: _Optional[int] = ..., state: _Optional[str] = ...) -> None: ...

class GetNodeTasksResponse(_message.Message):
    __slots__ = ("tasks",)
    class TasksEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: Task
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[Task, _Mapping]] = ...) -> None: ...
    TASKS_FIELD_NUMBER: _ClassVar[int]
    tasks: _containers.MessageMap[str, Task]
    def __init__(self, tasks: _Optional[_Mapping[str, Task]] = ...) -> None: ...
