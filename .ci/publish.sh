#!/bin/bash
set -ex
source .ci/common

docker pull ${CI_IMAGE_URI}

docker login -u "${DNAME}" -p "${DPASS}";
for TAG in $COMMIT $BRANCH; do
  TagAndPushImage "docker.io/${IMAGE}" $TAG;
done;
