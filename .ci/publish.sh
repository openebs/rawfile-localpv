#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "$0")"

set -exuo pipefail
source "$SCRIPT_DIR/common"

if [ -n "${DNAME:-}" ] && [ -n "${DPASS:-}" ]; then
  docker login -u "${DNAME}" -p "${DPASS}"
fi
for TAG in $COMMIT $BRANCH_SLUG; do
  TagAndPushImage "docker.io/${IMAGE}" $TAG;
done;
