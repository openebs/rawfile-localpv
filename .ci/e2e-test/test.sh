#!/bin/sh
set -ex

cd $(dirname $0)
curl --location https://dl.k8s.io/v1.18.1/kubernetes-test-linux-amd64.tar.gz | tar --strip-components=3 -zxf - kubernetes/test/bin/e2e.test kubernetes/test/bin/ginkgo

ssh-keygen -N "" -f $HOME/.ssh/id_rsa
cat $HOME/.ssh/id_rsa.pub >>$HOME/.ssh/authorized_keys

./e2e.test \
  -ginkgo.v \
  -ginkgo.focus='External.Storage' \
  -storage.testdriver=rawfile-driver.yaml \
  -report-dir report/
