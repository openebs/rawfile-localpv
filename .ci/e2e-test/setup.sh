#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "$0")"

set -ex
source "$SCRIPT_DIR/../common"


if [ "$(kubectl config current-context)" = "kind-rawfile" ]; then
  kind load docker-image $CI_IMAGE_URI --name "rawfile"
fi

helm upgrade --wait \
  -n openebs --create-namespace -i rawfile-csi \
  --set metrics.serviceMonitor.enabled=false \
  --set controller.image.repository=$CI_IMAGE_REPO,controller.image.tag=$CI_TAG,controller.image.pullPolicy=Never \
  --set node.image.repository=$CI_IMAGE_REPO,node.image.tag=$CI_TAG,node.image.pullPolicy=Never \
  "$SCRIPT_DIR/../../deploy/charts/rawfile-csi/"

kubectl wait --for=condition=ready pod --all -n openebs
kubectl get pods -n openebs -o wide
