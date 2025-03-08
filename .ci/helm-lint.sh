#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]:-"$0"}")")"
ROOT_DIR="$SCRIPT_DIR/.."
CHART_DIR="$ROOT_DIR/deploy/charts/rawfile-csi"

helm template "$CHART_DIR" --debug
helm lint "$CHART_DIR"
