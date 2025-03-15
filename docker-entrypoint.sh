#!/usr/bin/env bash

set -e

. "${PYSETUP_PATH}/.venv/bin/activate"

exec python -m rawfile "$@"
