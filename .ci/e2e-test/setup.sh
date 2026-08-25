#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "$0")"

set -ex
source "$SCRIPT_DIR/../common"

TAG="${CI_TEST_IMAGE_TAG}"
if [ -n "${CI_RELEASE_TAG:-}" ]; then
	TAG="$CI_RELEASE_TAG"
	TAG_SUFFIX=
fi
URI="$(build-image-uri ${TAG})"
TAG="$(build-image-tag ${TAG})"

echo "Image URI: $URI"
echo "Image Tag: $TAG"

if [ -n "${CI_RELEASE_TAG:-}" ]; then
	docker pull "$URI"
fi

CLUSTER_NAME="$(kubectl config current-context)"
if [[ "$CLUSTER_NAME" =~ ^kind-rawfile.* ]]; then
	kind load docker-image "$URI" --name "${CLUSTER_NAME#kind-}"
fi

CHART="$SCRIPT_DIR/../../deploy/helm/rawfile-localpv/"
if [ -n "${CI_CHART:-}" ]; then
	helm repo add rawfile-localpv "$CI_CHART"
	CHART="rawfile-localpv/rawfile-localpv --version ${TAG#v}"
fi

helm upgrade --wait \
	-n openebs --create-namespace -i rawfile-localpv \
	--set image.registry=$CI_REGISTRY,image.repository=$CI_IMAGE_REPO,image.tag=$TAG \
	--values "$SCRIPT_DIR/values.test.yaml" \
	$CHART

kubectl wait --for=condition=ready pod --all -n openebs
kubectl get pods -n openebs -o wide
