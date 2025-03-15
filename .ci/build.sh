#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "$0")"

set -exuo pipefail
source "$SCRIPT_DIR/common"

docker buildx build \
  --push --pull --no-cache \
  --platform="${CI_IMAGE_PLATFORMS}" \
  -t "$CI_IMAGE_URI" \
  --build-arg "IMAGE_REPOSITORY=${IMAGE}" \
  --build-arg "IMAGE_TAG=${COMMIT}" "$SCRIPT_DIR/.."

docker pull "$CI_IMAGE_URI"

if [ -n "${DNAME:-}" ] && [ -n "${DPASS:-}" ]; then
  docker login -u "${DNAME}" -p "${DPASS}";
  TagAndPushImage $CI_IMAGE_REPO $CI_TAG;
fi
