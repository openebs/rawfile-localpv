import pytest
from config.model import CSIDriverCmd, StoragePool
from pydantic import ValidationError


def test_pool_block_size_defaults_to_none(tmp_path):
    assert StoragePool(path=tmp_path).block_size is None


@pytest.mark.parametrize("block_size", [512, 1024, 2048, 4096])
def test_pool_block_size(tmp_path, block_size):
    assert StoragePool(path=tmp_path, block_size=block_size).block_size == block_size


@pytest.mark.parametrize("block_size", [0, 256, 1000, 8192])
def test_pool_block_size_invalid(tmp_path, block_size):
    with pytest.raises(ValidationError):
        StoragePool(path=tmp_path, block_size=block_size)


def test_pool_block_size_from_env_json(tmp_path):
    # As rendered by the chart in CSI_DRIVER__STORAGE_POOLS
    cmd = CSIDriverCmd(
        endpoint="unix:///csi/csi.sock",
        nodeid="node-1",
        plugin_type="controller",
        storage_pools=f'{{"default": {{"path": "{tmp_path}", "block_size": 4096}}}}',
    )

    assert cmd.storage_pools["default"].block_size == 4096
