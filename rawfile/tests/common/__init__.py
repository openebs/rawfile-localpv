import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def root_dir():
    current_file_path = Path(__file__).resolve()
    return current_file_path.parents[3]


def env_cleanup():
    clean = os.getenv("CLEAN")
    return not (clean is not None and clean.lower() in ("no", "false", "f", "0"))


def fixture_cleanup():
    return not hasattr(sys, "last_traceback")


def run(
    command: str,
    args: list[str] | None = None,
    capture_output=True,
    log_run=True,
    **kwargs,
):
    command = [command]
    if args is not None:
        command.extend(args)

    if log_run:
        logger.info(f"Running '{command}'")
    else:
        logger.debug(f"Running '{command}'")
    try:
        result = subprocess.run(
            command, capture_output=capture_output, check=True, text=True, **kwargs
        )
        logger.debug(
            f"Command '{command}' completed with:\nStdErr Output: {result.stderr}\nStdOut Output: {result.stdout}"
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        logger.error(
            f"Command '{command}' failed with exit code {e.returncode}\nStdErr Output: {e.stderr}\nStdOut Output: {e.stdout}"
        )
        raise

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise
