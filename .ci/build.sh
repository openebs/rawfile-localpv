#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "$0")"

set -exuo pipefail
source "$SCRIPT_DIR/common"

command -v docker &>/dev/null || ( echo 'Docker is not installed. Aborting.'; exit 1 )
docker buildx version &>/dev/null || ( echo 'Docker Buildx plugin is not installed. Aborting.'; exit 1 )

export PUSH_OPTION=""
export IMAGE_TAGS="${COMMIT}"

if [ "${CI_IMAGE_PLATFORMS}" = "local" ]; then
  export IMAGE_DESTINATION="docker"
else
  export IMAGE_DESTINATION="registry"
  if [ -n "${DNAME:-}" ] && [ -n "${DPASS:-}" ]; then
    docker login -u "${DNAME}" -p "${DPASS}"
    export PUSH_OPTION="--push"
  fi
  export IMAGE_TAGS="${COMMIT} ${BRANCH_SLUG}";
fi

for t in ${IMAGE_TAGS}; do
  TAGS_ARGS+=" -t ${CI_IMAGE_NAME}:${t}${TAG_SUFFIX:-}"
done

docker buildx build \
  --pull --no-cache ${PUSH_OPTION} \
  ${TAGS_ARGS} \
  --output=type=${IMAGE_DESTINATION} \
  --platform="${CI_IMAGE_PLATFORMS}" \
  --build-arg "IMAGE_REPOSITORY=${IMAGE}" \
  --build-arg "IMAGE_TAG=${COMMIT}" \
  "$SCRIPT_DIR/.."

if [ "${CI_IMAGE_PLATFORMS}" != "local" ]; then
  docker pull "$CI_IMAGE_URI"
fi

