#!/bin/bash
set -ex
source .ci/common

docker build -t $CI_IMAGE_URI --build-arg IMAGE_REPOSITORY=${IMAGE} --build-arg IMAGE_TAG=${COMMIT} .

docker login -u "${DNAME}" -p "${DPASS}";
TagAndPushImage $CI_IMAGE_REPO $CI_TAG;
