#!/usr/bin/env bash
# Build (and in CI publish) the base image defined in Dockerfile.base: the
# toolchain plus grpcio compiled against the FIPS OpenSSL. Tagged with a
# content hash of its inputs (see base-image-uri in .ci/common). Idempotent:
# exits early when that tag is already published. Run by the Container Images
# workflow ahead of .ci/build.sh, and by .ci/build.sh itself when no published
# base matches.

SCRIPT_DIR="$(dirname "$0")"
DREG=${DREG:-"docker.io"}
CI_REGISTRY="$DREG"

set -exuo pipefail
source "$SCRIPT_DIR/common"

command -v docker &>/dev/null || die 'Docker is not installed. Aborting.'
docker buildx version &>/dev/null || die 'Docker Buildx plugin is not installed. Aborting.'

export PUSH_OPTION=""
export ATTEST=""

if [ "${CI_IMAGE_PLATFORMS}" = "local" ]; then
	export IMAGE_DESTINATION="docker"
else
	export IMAGE_DESTINATION="registry"
	if base-image-published; then
		echo "Base image ${CI_BASE_IMAGE} already published; nothing to do."
		exit 0
	fi
	if [ -n "${DNAME:-}" ] && [ -n "${DPASS:-}" ]; then
		docker login -u "${DNAME}" -p "${DPASS}" "$CI_REGISTRY"
		export PUSH_OPTION="--push"
	fi
	export ATTEST="${ATTEST_OPTIONS}"
fi

docker buildx build \
	${PUSH_OPTION} \
	${ATTEST} \
	--pull \
	--output=type=${IMAGE_DESTINATION} \
	--platform="${CI_IMAGE_PLATFORMS}" \
	--build-arg "GRPCIO_VERSION=${GRPCIO_VERSION}" \
	-f "$SCRIPT_DIR/../Dockerfile.base" \
	-t "${CI_BASE_IMAGE}" \
	"$SCRIPT_DIR/.."
