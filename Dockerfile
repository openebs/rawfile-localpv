FROM python:3.10-slim-buster as builder
RUN apt-get update && apt-get install -y build-essential libbtrfsutil-dev
RUN pip wheel -w /wheels "https://github.com/kdave/btrfs-progs/archive/refs/tags/v5.16.1.tar.gz#egg=btrfsutil&subdirectory=libbtrfsutil/python"

FROM python:3.10-slim-buster

WORKDIR /app/

RUN apt-get update && \
    apt-get install -y e2fsprogs btrfs-progs libbtrfsutil1 xfsprogs && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels/ /wheels/
RUN pip install /wheels/*
RUN wget -O /usr/local/bin/btdu bthttps://github.com/CyberShadow/btdu/releases/download/v0.4.1/btdu-static-x86_64

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
