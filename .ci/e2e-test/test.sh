#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "$0")"

set -ex

K8S_VERSION=$(cat "$SCRIPT_DIR/../../.kube-version")
K8S_CLUSTER=${K8S_CLUSTER:-"kind"}

DOWNLOAD="true"
if [ -f "$SCRIPT_DIR/e2e.test" ]; then
  if [ "$("$SCRIPT_DIR/e2e.test" -version)" = "$K8S_VERSION" ] && [ -f "$SCRIPT_DIR/ginkgo" ]; then
    DOWNLOAD="false"
  fi
fi

cd $(dirname $0)
if [ "$DOWNLOAD" = "true" ]; then
  command -v curl >/dev/null 2>&1 || { echo >&2 "curl is not installed. Aborting."; exit 1; }
  curl --location https://dl.k8s.io/$K8S_VERSION/kubernetes-test-linux-amd64.tar.gz | tar --strip-components=3 --no-same-owner -zxf - kubernetes/test/bin/e2e.test kubernetes/test/bin/ginkgo
fi

if [ "$K8S_CLUSTER" = "kind" ]; then
  export KUBE_SSH_USER=root
  export KUBE_SSH_KEY=$(pwd)/ssh_id
fi

if [ -z "$KUBECONFIG" ]; then
  export KUBECONFIG="$HOME/.kube/config"
fi

# Taken from: https://kubernetes.io/blog/2020/01/08/testing-of-csi-drivers/
./ginkgo -p -v \
  -focus='External.Storage' \
  -skip='\[Feature:|\[Disruptive\]|\[Serial\]' \
  --fail-fast \
  ./e2e.test \
  -- \
  -storage.testdriver=rawfile-driver.yaml

./ginkgo -v \
  -focus='External.Storage.*(\[Feature:|\[Disruptive\]|\[Serial\])' \
  --fail-fast \
  ./e2e.test \
  -- \
  -storage.testdriver=rawfile-driver.yaml
