FROM python:3-alpine3.11

WORKDIR /app/

ENV PIP_NO_CACHE_DIR 1
ADD ./requirements.txt ./
RUN apk add --no-cache gcc linux-headers make musl-dev python-dev g++
RUN pip install -r ./requirements.txt

ADD ./ ./

ENTRYPOINT ["/usr/bin/env", "python3", "/app/rawfile.py"]
CMD ["csi-driver"]
