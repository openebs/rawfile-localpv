#!/usr/bin/env bash
#
# Build and publish the FIPS base image defined in Dockerfile.fips-base.
#
# This is decoupled from the application build: .ci/build.sh does NOT call this.
# The application Dockerfile pins a published tag of this image, so the
# expensive FIPS/grpcio build only runs when the base inputs change (driven by
# .github/workflows/fips-base-image.yml or manually by a maintainer).
#
# The tag is a content hash of the inputs (Dockerfile.fips-base and the locked
# grpcio version).
#
# Usage:
#   .ci/build-fips-base.sh tag     # print the image uri for the current inputs
#   .ci/build-fips-base.sh check   # fail if Dockerfile does not pin that uri
#   .ci/build-fips-base.sh build   # build (local) or build+push (CI_TEST=false)

SCRIPT_DIR="$(dirname "$0")"
DREG=${DREG:-"docker.io"}
CI_REGISTRY="$DREG"

set -euo pipefail
source "$SCRIPT_DIR/common"

ROOT="$SCRIPT_DIR/.."
FIPS_BASE_IMAGE="$(fips-base-image-uri)"

pinned-base-image() {
	sed -n 's/^ARG BASE_IMAGE=\(.*\)$/\1/p' "$ROOT/Dockerfile"
}

cmd="${1:-build}"
case "$cmd" in
tag)
	echo "$FIPS_BASE_IMAGE"
	;;
check)
	pinned="$(pinned-base-image)"
	if [ "$pinned" != "$FIPS_BASE_IMAGE" ]; then
		die "Dockerfile pins BASE_IMAGE=${pinned}
but the FIPS base inputs hash to      ${FIPS_BASE_IMAGE}
Publish the new base (.ci/build-fips-base.sh build) and update the ARG BASE_IMAGE pin in Dockerfile."
	fi
	echo "Dockerfile BASE_IMAGE pin is up to date: $FIPS_BASE_IMAGE"
	;;
build)
	command -v docker &>/dev/null || die 'Docker is not installed. Aborting.'
	docker buildx version &>/dev/null || die 'Docker Buildx plugin is not installed. Aborting.'

	PUSH_OPTION=""
	if [ "${CI_IMAGE_PLATFORMS}" = "local" ]; then
		IMAGE_DESTINATION="docker"
	else
		IMAGE_DESTINATION="registry"
		if docker buildx imagetools inspect "$FIPS_BASE_IMAGE" &>/dev/null; then
			echo "FIPS base image already published: $FIPS_BASE_IMAGE"
			exit 0
		fi
		if [ -n "${DNAME:-}" ] && [ -n "${DPASS:-}" ]; then
			docker login -u "${DNAME}" -p "${DPASS}" "$CI_REGISTRY"
			PUSH_OPTION="--push"
		fi
	fi

	set -x
	docker buildx build \
		-f "$ROOT/Dockerfile.fips-base" \
		-t "$FIPS_BASE_IMAGE" \
		${PUSH_OPTION} \
		--output=type=${IMAGE_DESTINATION} \
		--platform="${CI_IMAGE_PLATFORMS}" \
		--build-arg "GRPCIO_VERSION=$(fips-base-grpcio-version)" \
		"$ROOT"
	;;
*)
	die "Unknown command '$cmd'. Usage: $0 {tag|check|build}"
	;;
esac
