from typing import Any, TypeAlias

from pydantic import BaseModel, IPvAnyAddress


class PoolStat(BaseModel):
    reserved_capacity: str
    path: str
    reserved_capacity_mode: str
    capacity: int
    copy_on_write_supported: bool


PoolsStat: TypeAlias = dict[str, PoolStat]


class Node(BaseModel):
    name: str
    ip: IPvAnyAddress
    pools_stat: PoolsStat | None = None
    online: bool


NodeList: TypeAlias = list[Node]


class VolumeStat(BaseModel):
    name: str
    size: int
    copy_on_write: bool
    thin_provision: bool
    ready: bool
    deleted_at: float
    gc_at: float
    created_at: float
    freezefs: bool
    storage_pool: str
    img_file: str
    used: int
    logical_size: int
    physical_size: int


VolumesStat: TypeAlias = list[VolumeStat]


class Task(BaseModel):
    task: str
    args: list[str] | None = None
    kwargs: dict[str, Any] | None = None
    retry_count: int = 0
    state: str


TasksList: TypeAlias = dict[str, Task]
