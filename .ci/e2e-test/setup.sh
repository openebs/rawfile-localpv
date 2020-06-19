#!/bin/bash
set -ex
source .ci/common

curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/v1.18.1/bin/linux/amd64/kubectl && chmod +x kubectl && sudo mv kubectl /usr/local/bin/
sudo apt update && sudo apt install -y conntrack
curl -Lo minikube https://storage.googleapis.com/minikube/releases/v1.8.1/minikube-linux-amd64 && chmod +x minikube && sudo mv minikube /usr/local/bin/
mkdir -p $HOME/.kube $HOME/.minikube
touch $KUBECONFIG
sudo minikube start --profile=minikube --vm-driver=none --kubernetes-version=v1.18.1
minikube update-context --profile=minikube
chown -R travis: /home/travis/.minikube/
eval "$(minikube docker-env --profile=minikube)" && export DOCKER_CLI='docker'

curl -fsSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash

helm upgrade --wait \
  -n kube-system -i rawfile-csi \
  --set serviceMonitor.enabled=false \
  --set controller.image.repository=$CI_IMAGE_REPO --set controller.image.tag=$CI_TAG \
  --set node.image.repository=$CI_IMAGE_REPO --set node.image.tag=$CI_TAG \
  ./deploy/charts/rawfile-csi/
