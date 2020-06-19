#!/bin/sh
set -ex

cd $(dirname $0)
curl --location https://dl.k8s.io/v1.18.1/kubernetes-test-linux-amd64.tar.gz | tar --strip-components=3 -zxf - kubernetes/test/bin/e2e.test kubernetes/test/bin/ginkgo

ssh-keygen -N "" -f $HOME/.ssh/id_rsa
cat $HOME/.ssh/id_rsa.pub >>$HOME/.ssh/authorized_keys

# Taken from: https://kubernetes.io/blog/2020/01/08/testing-of-csi-drivers/
./ginkgo -p -v \
  -focus='External.Storage' \
  -skip='\[Feature:|\[Disruptive\]|\[Serial\]' \
  ./e2e.test \
  -- \
  -storage.testdriver=rawfile-driver.yaml

./ginkgo -v \
  -focus='External.Storage.*(\[Feature:|\[Disruptive\]|\[Serial\])' \
  ./e2e.test \
  -- \
  -storage.testdriver=rawfile-driver.yaml
