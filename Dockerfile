# Application image. Builds on top of the pre-published FIPS base image
# (Dockerfile.fips-base, published by .github/workflows/fips-base-image.yml),
# which provides:
#   * system OpenSSL switched into FIPS mode (OPENSSL_CONF)
#   * a pre-built grpcio wheel linked against system OpenSSL in /wheels
#
# The tag is a content hash of the base inputs. When Dockerfile.fips-base or the
# locked grpcio version changes, the base workflow publishes a new tag; bump the
# pin here to pick it up (`.ci/build-fips-base.sh tag` prints the expected tag).
ARG BASE_IMAGE=docker.io/openebs/rawfile-localpv-base:fips-0291934e28d8
FROM ${BASE_IMAGE} AS python-base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

FROM python-base AS builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    build-essential

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR $PYSETUP_PATH
COPY ./poetry.lock ./pyproject.toml ./
# Seed the venv with the FIPS grpcio wheel from the base image, then let Poetry
# install everything else. Poetry skips grpcio because the locked version is
# already present; `no-binary` guards against it ever being re-fetched from PyPI.
RUN python -m venv "$VENV_PATH" && \
    "$VENV_PATH/bin/pip" install --no-index --no-deps --find-links /wheels grpcio && \
    poetry config installer.no-binary grpcio && \
    poetry install --only main --no-root

FROM python-base AS production

COPY --from=builder-base $VENV_PATH $VENV_PATH

# Fail the build if grpcio is not linked against the system (FIPS) OpenSSL.
RUN CYGRPC="$(find "$VENV_PATH" -name 'cygrpc*.so' | head -n1)" && \
    test -n "$CYGRPC" && \
    ldd "$CYGRPC" | grep -q 'libssl\.so' && \
    ldd "$CYGRPC" | grep -q 'libcrypto\.so' && \
    ! nm -D "$CYGRPC" | grep -qi 'boringssl' && \
    python -c 'import grpc; print("grpcio", grpc.__version__, "linked to system OpenSSL")'

COPY ./rawfile /rawfile
WORKDIR /rawfile

RUN python -m \
    grpc_tools.protoc \
    --proto_path=protos/ \
    protos/csi.proto \
    --grpc_python_out=csi/ \
    --python_out=csi/ \
    --pyi_out=csi/ && \
    python -m \
    grpc_tools.protoc \
    --proto_path=protos/ \
    protos/internal.proto \
    --grpc_python_out=internal/ \
    --python_out=internal/ \
    --pyi_out=internal/ && \
    python utils/fallocate/build.py
COPY docker-entrypoint.sh /docker-entrypoint.sh

ARG IMAGE_TAG
ARG PROVISIONER_VERSION
ENV PROVISIONER_VERSION=${PROVISIONER_VERSION}

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["csi-driver"]
