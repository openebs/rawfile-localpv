FROM python:3.11-slim-buster as builder
RUN apt-get update && apt-get install -y build-essential libbtrfsutil-dev
RUN pip wheel -w /wheels "https://github.com/kdave/btrfs-progs/archive/refs/tags/v6.3.2.tar.gz#egg=btrfsutil&subdirectory=libbtrfsutil/python"

FROM python:3.11-slim-buster

WORKDIR /app/

RUN apt-get update && \
    apt-get install -y e2fsprogs btrfs-progs libbtrfsutil1 xfsprogs && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels/ /wheels/
RUN pip install /wheels/*

ENV PIP_NO_CACHE_DIR 1
ADD ./requirements.txt ./
RUN pip install -r ./requirements.txt

ADD ./ ./

ENTRYPOINT ["/usr/bin/env", "python3", "/app/rawfile.py"]
CMD ["csi-driver"]
ENV PYTHONUNBUFFERED 1


ARG IMAGE_TAG
ARG IMAGE_REPOSITORY
ENV IMAGE_REPOSITORY ${IMAGE_REPOSITORY}
ENV IMAGE_TAG ${IMAGE_TAG}
