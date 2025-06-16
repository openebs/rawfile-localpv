#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "$0")"
ROOT_DIR="$SCRIPT_DIR"/..

set -euo pipefail

cd "$ROOT_DIR/rawfile/tests"

# Extra arguments will be provided directly to pytest, otherwise the bdd folder will be tested with default arguments
if [ $# -eq 0 ]; then
  pytest test_smoke.py --junit-xml="./report.xml" --durations=20
else
  pytest test_smoke.py "$@" --junit-xml="./report.xml" --durations=20
fi
