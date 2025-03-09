#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(dirname "$0")"

TMP_KIND=${TMP_KIND:-"/tmp/kind/rawfile/"}
TMP_KIND_CONFIG="$TMP_KIND/config.yaml"
WORKERS=1
DRY_RUN=
KIND="kind"
KUBECTL="kubectl"
DOCKER="docker"
CLEANUP="false"
SUDO=${SUDO:-"sudo"}
# todo: make configurable
K8S_VERSION=${K8S_VERSION:-v1.27.0}

help() {
  cat <<EOF
Usage: $(basename "$0") [COMMAND] [OPTIONS]

Options:
  -h, --help                        Display this text.
  --workers       <num>             The number of worker nodes (Default: $WORKERS).
  --dry-run                         Don't do anything, just output steps.
  --cleanup                         Prior to starting, stops the running instance of the deployer.

Command:
  start                             Start the k8s cluster.
  stop                              Stop the k8s cluster.

Examples:
  $(basename "$0") start --workers 2
EOF
}

echo_stderr() {
  echo -e "${1}" >&2
}

die() {
  local _return="${2:-1}"
  echo_stderr "$1"
  exit "${_return}"
}

COMMAND=
DO_ARGS=
while [ "$#" -gt 0 ]; do
  case $1 in
    -h|--help)
      help
      exit 0
      shift;;
    start)
      [ -n "$COMMAND" ] && die "Command already specified"
      COMMAND="start"
      DO_ARGS="y"
      shift;;
    stop)
      [ -n "$COMMAND" ] && die "Command already specified"
      COMMAND="stop"
      DO_ARGS="y"
      shift;;
    *)
      [ -z "$DO_ARGS" ] && die "Must specify command before args"
      case $1 in
        --workers)
          shift
          test $# -lt 1 && die "Missing Number of Workers"
          WORKERS=$1
          shift;;
        --cleanup)
          CLEANUP="true"
          shift;;
        --dry-run)
          if [ -z "$DRY_RUN" ]; then
            DRY_RUN="--dry-run"
            KIND="echo $KIND"
            FALLOCATE="echo $FALLOCATE"
            KUBECTL="echo $KUBECTL"
            DOCKER="echo $DOCKER"
            SUDO="echo"
          fi
          shift;;
        *)
          die "Unknown cli argument: $1"
          ;;
      esac
  esac
done

if [ -z "$COMMAND" ]; then
  die "No command specified!\n$(help)"
fi

if [ "$COMMAND" = "stop" ] || [ "$CLEANUP" = "true" ]; then
  $KIND delete cluster --name "rawfile"
  if [ "$COMMAND" = "stop" ]; then
    exit 0
  fi
fi

# Create and cleanup the tmp folder
# Note: this is static in case you want to restart the worker node
mkdir -p "$TMP_KIND"
$SUDO rm -rf "$TMP_KIND"/*

# Adds the control-plane/master node
cat <<EOF > "$TMP_KIND_CONFIG"
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  image: kindest/node:$K8S_VERSION
EOF

start_core=1
nodes=()
for node_index in $(seq 1 $WORKERS); do
  if [ "$node_index" == 1 ]; then
    node="rawfile-worker"
  else
    node="rawfile-worker$node_index"
  fi
  nodes+=($node)

  host_path="$TMP_KIND/$node"
  cat <<EOF >> "$TMP_KIND_CONFIG"
- role: worker
  image: kindest/node:$K8S_VERSION
  extraMounts:
    - hostPath: /dev
      containerPath: /dev
      propagation: HostToContainer
    - hostPath: $host_path
      containerPath: /var/csi/rawfile
      propagation: HostToContainer
EOF
done

if [ -n "$DRY_RUN" ]; then
  cat "$TMP_KIND_CONFIG"
fi

$KIND create cluster --config "$TMP_KIND_CONFIG" --name "rawfile"

$KUBECTL cluster-info --context kind-rawfile
if [ -z "$DRY_RUN" ]; then
  host_ip=$($DOCKER network inspect kind | jq -r 'first (.[0].IPAM.Config[].Gateway | select(.))')
fi
echo "HostIP: $host_ip"

# shellcheck disable=SC2068
for node in ${nodes[@]}; do
  $DOCKER exec "$node" mount -o remount,rw /sys

  # Note: this will go away if the node restarts...
  $DOCKER exec "$node" bash -c 'printf "'"$host_ip"' kvmhost\n" >> /etc/hosts'

  # SSH access is required by the e2e test disruptive storage tests
  docker exec "$node" apt update
  docker exec "$node" apt install -y -q openssh-server
  docker exec "$node" mkdir -p /root/.ssh
  docker exec "$node" sh -c 'cat /etc/ssh/ssh_host_rsa_key.pub > /root/.ssh/authorized_keys'
  docker cp "$node":/etc/ssh/ssh_host_rsa_key "$SCRIPT_DIR/e2e-test/ssh_id"
  docker exec "$node" systemctl restart sshd
done
