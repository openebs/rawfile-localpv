ARG IMAGE_TAG
ARG IMAGE_REPOSITORY
FROM python:3.8.3-slim-buster

WORKDIR /app/

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
