import subprocess
from datetime import UTC, datetime
from typing import Any

from .logs import logger


def run(
    cmd: str, executable: str | None = None, check=True, capture_output=True, log=True
):
    start = datetime.now(UTC)
    kwargs: dict[str, Any] = {
        "check": check,
        "capture_output": capture_output,
        "shell": True,
    }
    log_ctx: dict[str, Any] = {
        "check": check,
        "capture_output": capture_output,
        "command": cmd,
        "start": start,
    }
    if executable is not None:
        kwargs["executable"] = executable
        log_ctx["executable"] = executable

    output = subprocess.run(cmd, **kwargs)  # noqa: PLW1510 ## check is in kwargs
    end = datetime.now(UTC)
    log_ctx.update(
        {
            "returncode": output.returncode,
            "end": end,
            "latency": end - start,
        }
    )
    if capture_output:
        log_ctx.update(
            {
                "stderr": output.stderr.decode(),
                "stdout": output.stdout.decode(),
            }
        )
    if log:
        logger.debug("Shell command execution", **log_ctx)
    return output
