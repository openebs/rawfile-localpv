#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "$0")"
ROOT_DIR="$SCRIPT_DIR"/..

set -euo pipefail

# Build the fallocate extension next to the sources (on PYTHONPATH), as the Dockerfile does
(cd "$ROOT_DIR/rawfile" && python utils/fallocate/build.py)

cd "$ROOT_DIR/rawfile/tests"

# Unit tests need no cluster, extra arguments are provided directly to pytest
pytest unit "$@"
