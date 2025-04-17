#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "$0")"

set -ex
source "$SCRIPT_DIR/../common"


if [ "$(kubectl config current-context)" = "kind-rawfile" ]; then
  kind load docker-image $(build-image-uri ${CI_TEST_IMAGE_TAG}) --name "rawfile"
fi

helm upgrade --wait \
  -n openebs --create-namespace -i rawfile-csi \
  --set metrics.serviceMonitor.enabled=false \
  --set image.registry=$CI_REGISTRY,image.repository=$CI_IMAGE_REPO,image.tag=$(build-image-tag $CI_TEST_IMAGE_TAG),image.pullPolicy=Never \
  "$SCRIPT_DIR/../../deploy/charts/rawfile-csi/"

kubectl wait --for=condition=ready pod --all -n openebs
kubectl get pods -n openebs -o wide
