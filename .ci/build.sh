#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "$0")"

set -exuo pipefail
source "$SCRIPT_DIR/common"

export IMAGE_DESTINATION="registry"
if [ "${CI_IMAGE_PLATFORMS}" = "local" ]; then
  export IMAGE_DESTINATION="docker"
fi

docker buildx build \
  --pull --no-cache \
  --output=type=${IMAGE_DESTINATION} \
  --platform="${CI_IMAGE_PLATFORMS}" \
  -t "$CI_IMAGE_URI" \
  --build-arg "IMAGE_REPOSITORY=${IMAGE}" \
  --build-arg "IMAGE_TAG=${COMMIT}" "$SCRIPT_DIR/.."

if [ "${CI_IMAGE_PLATFORMS}" != "local" ]; then
  docker pull "$CI_IMAGE_URI"
fi

if [ -n "${DNAME:-}" ] && [ -n "${DPASS:-}" ]; then
  docker login -u "${DNAME}" -p "${DPASS}";
  TagAndPushImage $CI_IMAGE_REPO $CI_TAG;
fi
