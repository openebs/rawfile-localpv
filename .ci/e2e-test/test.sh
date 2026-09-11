#!/usr/bin/env bash

SCRIPT_DIR="$(dirname "$0")"
source "$SCRIPT_DIR/common"
set -ex

K8S_VERSION=$(cat "$SCRIPT_DIR/../../.kube-version")
K8S_CLUSTER=${K8S_CLUSTER:-"kind"}
JUNIT_REPORT_DIR=${JUNIT_REPORT_DIR:-/tmp/ginkgo-junit}

DOWNLOAD="true"
if [ -f "$SCRIPT_DIR/e2e.test" ]; then
	if [ "$("$SCRIPT_DIR/e2e.test" -version)" = "$K8S_VERSION" ] && [ -f "$SCRIPT_DIR/ginkgo" ]; then
		DOWNLOAD="false"
	fi
fi

cd $(dirname $0)
if [ "$DOWNLOAD" = "true" ]; then
	command -v curl >/dev/null 2>&1 || die "curl is not installed. Aborting."
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
run_basic() {
	./ginkgo -p -v \
		-focus='External.Storage' \
		-skip='\[Feature:|\[Disruptive\]|\[Serial\]' \
		--fail-fast \
		--junit-report="${JUNIT_REPORT_DIR}/basic.xml" \
		./e2e.test \
		-- \
		-storage.testdriver=rawfile-driver.yaml
}

run_advanced() {
	./ginkgo -v \
		-focus='External.Storage.*(\[Feature:|\[Disruptive\]|\[Serial\])' \
		--fail-fast \
		--junit-report="${JUNIT_REPORT_DIR}/advanced.xml" \
		./e2e.test \
		-- \
		-storage.testdriver=rawfile-driver.yaml
}

# Usage: test.sh [basic|advanced]
# Without arguments both suites are run.
case "${1:-all}" in
basic)
	run_basic
	;;
advanced)
	run_advanced
	;;
all)
	run_basic
	run_advanced
	;;
*)
	die "Unknown e2e suite: $1 (expected basic or advanced)"
	;;
esac
