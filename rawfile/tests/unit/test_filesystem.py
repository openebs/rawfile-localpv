import os
import shutil
import subprocess
import time

import pytest
from filesystem.utils import get_device_fs

pytestmark = pytest.mark.skipif(not shutil.which("blkid"), reason="needs blkid")


@pytest.fixture
def image(tmp_path):
    image = tmp_path / "disk.img"
    image.write_bytes(bytes(1024**2))
    return image


@pytest.mark.skipif(not shutil.which("mkfs.ext4"), reason="needs mkfs.ext4")
def test_get_device_fs(image):
    subprocess.run(["mkfs.ext4", "-q", "-F", image], check=True)

    assert get_device_fs(image.as_posix()) == "ext4"


def test_get_device_fs_without_filesystem(image):
    assert get_device_fs(image.as_posix()) is None


def test_get_device_fs_ignores_blkid_cache(image, tmp_path, monkeypatch):
    # The entry blkid's cache holds for a loop device it probed less than 2s ago,
    # and which has been re-attached to an empty image since. blkid trusts it, as
    # the device wasn't modified after the probe.
    old = time.time() - 60
    os.utime(image, (old, old))
    cache = tmp_path / "blkid.tab"
    cache.write_text(
        f'<device DEVNO="0x0000" TIME="{int(time.time())}.0" TYPE="ext4">'
        f"{image}</device>\n"
    )
    monkeypatch.setenv("BLKID_FILE", cache.as_posix())

    assert get_device_fs(image.as_posix()) is None
