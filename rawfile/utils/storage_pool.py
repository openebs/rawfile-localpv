from collections.abc import Callable

from config import config
from pydantic import ByteSize

from utils.devices import statvfs
from utils.modeltypes import ReservedCapacityMode
from utils.volume_manager import manager as volume_manager


# if the mode is "plain", reserved capacity is taken as specified in config
def plain_reserved_capacity_handler(
    disk_total_size: int, reserved_capacity: ByteSize | str
) -> int:
    if isinstance(reserved_capacity, str):
        return disk_total_size * int(reserved_capacity[:-1]) / 100
    elif isinstance(reserved_capacity, ByteSize):
        return reserved_capacity.to("B")


# if the mode is "subtract-from-total", reserved capacity is taken as (total - specified in config)
def subtract_from_total_reserved_capacity_handler(
    disk_total_size: int, reserved_capacity: ByteSize | str
) -> int:
    if isinstance(reserved_capacity, str):
        return disk_total_size - disk_total_size * int(reserved_capacity[:-1]) / 100
    elif isinstance(reserved_capacity, ByteSize):
        return disk_total_size - reserved_capacity.to("B")


reserved_capacity_handlers: dict[
    ReservedCapacityMode, Callable[[int, ByteSize | str], int]
] = {
    ReservedCapacityMode.PLAIN: plain_reserved_capacity_handler,
    ReservedCapacityMode.SUBTRACT_FROM_TOTAL: subtract_from_total_reserved_capacity_handler,
}


def get_capacity(storage_pool: str | None = None):
    if not storage_pool:
        storage_pool = config.csi_driver.default_pool
    pool = config.csi_driver.storage_pools[storage_pool]
    stats = statvfs(pool.path)
    disk_total_size = stats["fs_size"]
    disk_free_size = stats["fs_avail"]
    reserved_capacity_config = pool.reserved_capacity
    reserved_capacity_mode = pool.reserved_capacity_mode

    # reserved_capacity is the capacity reserved for everything else but this pool
    # so the capacity reserved for this pool is (disk_total_size - reserved_capacity)
    reserved_capacity = reserved_capacity_handlers[reserved_capacity_mode](
        disk_total_size, reserved_capacity_config
    )

    volumes_physical_size = 0

    volume_stats_values = volume_manager.get_volumes_stats_by_pool(
        storage_pool
    ).values()
    for volume_stat in volume_stats_values:
        # if the backing file is sparse, count only the defacto allocated blocks
        # if not, count the whole thing
        volumes_physical_size += volume_stat["physical_size"]

    capacity = max(
        min(
            disk_total_size - reserved_capacity - volumes_physical_size, disk_free_size
        ),
        0,
    )
    return capacity
