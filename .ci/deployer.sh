#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(dirname "$0")"

source "${SCRIPT_DIR}/common"

CLUSTER_NAME="rawfile"
WORKERS=1
DRY_RUN=
KIND="kind"
KUBECTL="kubectl"
DOCKER="docker"
CLEANUP="false"
SUDO=${SUDO:-"sudo"}
RAW_SIZE="100GiB"
K8S_VERSION=$(cat "$SCRIPT_DIR/../.kube-version")
INS_SSH="true"

command -v "$KIND" >/dev/null 2>&1 || die "kind is not installed. Aborting."
command -v "$KUBECTL" >/dev/null 2>&1 || die "kubectl is not installed. Aborting."

help() {
	cat <<EOF
Usage: $(basename "$0") [COMMAND] [OPTIONS]

Options:
  -h, --help                        Display this text.
  --workers       <num>             The number of worker nodes (Default: $WORKERS).
  --dry-run                         Don't do anything, just output steps.
  --cleanup                         Prior to starting, stops the running instance of the deployer.
  --loop-size     <size>            Size of the rawfile backend for each worker node (Default: $RAW_SIZE).
  --name          <string>          Name of the cluster to issue commands on.
  --no-ssh                          Don't install SSH on the worker nodes (Default: false).

Command:
  start                             Start the k8s cluster.
  stop                              Stop the k8s cluster.

Examples:
  $(basename "$0") start --workers 2
EOF
}

COMMAND=
DO_ARGS=
while [ "$#" -gt 0 ]; do
	case $1 in
	-h | --help)
		help
		exit 0
		shift
		;;
	start)
		[ -n "$COMMAND" ] && die "Command already specified"
		COMMAND="start"
		DO_ARGS="y"
		shift
		;;
	stop)
		[ -n "$COMMAND" ] && die "Command already specified"
		COMMAND="stop"
		DO_ARGS="y"
		shift
		;;
	*)
		[ -z "$DO_ARGS" ] && die "Must specify command before args"
		case $1 in
		--name)
			shift
			test $# -lt 1 && die "Missing Name of the Cluster"
			CLUSTER_NAME=$1
			shift
			;;
		--no-ssh)
			INS_SSH="false"
			shift
			;;
		--workers)
			shift
			test $# -lt 1 && die "Missing Number of Workers"
			WORKERS=$1
			shift
			;;
		--cleanup)
			CLEANUP="true"
			shift
			;;
		--loop-size)
			shift
			test $# -lt 1 && die "Missing Loop Size"
			RAW_SIZE=$1
			shift
			;;
		--dry-run)
			if [ -z "$DRY_RUN" ]; then
				DRY_RUN="--dry-run"
				KIND="echo $KIND"
				FALLOCATE="echo $FALLOCATE"
				KUBECTL="echo $KUBECTL"
				DOCKER="echo $DOCKER"
				SUDO="echo"
			fi
			shift
			;;
		*)
			die "Unknown cli argument: $1"
			;;
		esac
		;;
	esac
done

TMP_KIND=${TMP_KIND:-"/tmp/kind/$CLUSTER_NAME"}
TMP_KIND_CONFIG="$TMP_KIND/config.yaml"

if [ -z "$COMMAND" ]; then
	die "No command specified!\n$(help)"
fi

if [ "$COMMAND" = "stop" ] || [ "$CLEANUP" = "true" ]; then
	$KIND delete cluster --name "$CLUSTER_NAME"
	if [ "$COMMAND" = "stop" ]; then
		exit 0
	fi
fi

# Create and cleanup the tmp folder
# Note: this is static in case you want to restart the worker node
mkdir -p "$TMP_KIND"
$SUDO rm -rf "$TMP_KIND"/*

# Adds the control-plane/master node
cat <<EOF >"$TMP_KIND_CONFIG"
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
kubeadmConfigPatches:
- |
  apiVersion: kubelet.config.k8s.io/v1beta1
  kind: KubeletConfiguration
  syncFrequency: 10s
nodes:
- role: control-plane
  image: kindest/node:$K8S_VERSION
EOF

start_core=1
nodes=()
for node_index in $(seq 1 $WORKERS); do
	if [ "$node_index" == 1 ]; then
		node="$CLUSTER_NAME-worker"
	else
		node="$CLUSTER_NAME-worker$node_index"
	fi
	nodes+=($node)

	host_path="$TMP_KIND/rawfile-mnt/$node"
	mkdir -p "$host_path"

	truncate -s "$RAW_SIZE" "$host_path/rawfile.img"
	mkfs.xfs -m reflink=1 "$host_path/rawfile.img" >/dev/null

	cat <<EOF >>"$TMP_KIND_CONFIG"
- role: worker
  image: kindest/node:$K8S_VERSION
  # kubeadmConfigPatches:
  # - |
  #   kind: JoinConfiguration
  #   nodeRegistration:
  #     kubeletExtraArgs:
  #       v: "5"
  extraMounts:
    - hostPath: /dev
      containerPath: /dev
      propagation: HostToContainer
    - hostPath: $host_path/rawfile.img
      containerPath: /var/local/openebs/rawfile/default-pool.img
      propagation: HostToContainer
EOF
done

if [ -n "$DRY_RUN" ]; then
	cat "$TMP_KIND_CONFIG"
fi

$KIND create cluster --config "$TMP_KIND_CONFIG" --name "$CLUSTER_NAME"

export KUBECONFIG="$TMP_KIND/kubeconfig"
$KIND export kubeconfig --name "$CLUSTER_NAME"

$KUBECTL cluster-info --context "kind-$CLUSTER_NAME"

# shellcheck disable=SC2068
for node in ${nodes[@]}; do
	$DOCKER exec "$node" mount -o remount,rw /sys

	$DOCKER exec "$node" sh -c "mkdir /var/local/openebs/rawfile/default-pool; mount /var/local/openebs/rawfile/default-pool.img /var/local/openebs/rawfile/default-pool"

	if [ "$INS_SSH" = "false" ]; then
		continue
	fi
	# SSH access is required by the e2e test disruptive storage tests
	$DOCKER exec "$node" apt update
	$DOCKER exec "$node" apt install -y -q openssh-server
	$DOCKER exec "$node" mkdir -p /root/.ssh
	$DOCKER exec "$node" sh -c 'cat /etc/ssh/ssh_host_rsa_key.pub > /root/.ssh/authorized_keys'
	$DOCKER cp "$node":/etc/ssh/ssh_host_rsa_key "$SCRIPT_DIR/e2e-test/ssh_id"
	$DOCKER exec "$node" systemctl restart sshd
done

echo
echo "You can use the following command to restrict your KUBECONFIG to this cluster:"
echo "export KUBECONFIG=\"$TMP_KIND/kubeconfig\""
