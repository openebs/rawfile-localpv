# check=skip=InvalidDefaultArgInFrom
# rawfile-localpv container image, built on Red Hat Hummingbird FIPS images.
#
# Stages:
#   xfs-donor - xfsprogs is not packaged for Hummingbird; take Fedora's build
#               (glibc 2.42 < Hummingbird's 2.43, so ABI-compatible) plus the
#               few shared libs it needs that Hummingbird does not ship.
#   runtime   - hi/python:<ver>-fips: FIPS-enabled Python runtime. Ships no
#               shell or package manager, so the OS tools rawfile shells out to
#               are added with `dnf --installroot` in the builder (keeping the
#               rpmdb consistent) and the result becomes the final image.
#   builder   - BASE_IMAGE (Dockerfile.base: builder image, toolchain, Poetry
#               and the grpcio wheel compiled against the FIPS OpenSSL) plus
#               the Python deps, the cffi fallocate helper, the protobuf stubs
#               and the assembled runtime rootfs.
#   production- the assembled rootfs, venv and application.
#
# Build with .ci/build.sh, which supplies BASE_IMAGE (see .ci/common).
#
# FIPS: OpenSSL in these images runs with the FIPS provider active and
# `default_properties = fips=yes` (crypto-policies state FIPS). Python's
# ssl/hashlib and the source-built grpcio all go through that libcrypto.
#
# Image pins: upstream images are pinned by digest and bumped together by
# Dependabot (grouped, weekly; Dockerfile.base included), so builder and
# runtime always come from the same Hummingbird publish, builds are
# reproducible from the commit, and an upstream rebuild is a reviewed PR
# rather than a silent change.
#
# BASE_IMAGE deliberately has no default so a bare `docker build` fails
# instead of guessing a base; the check directive at the top of this file
# silences the linter warning about that.
ARG BASE_IMAGE

# registry.fedoraproject.org/fedora:43
FROM registry.fedoraproject.org/fedora:43@sha256:0acca761d5c919be62a2aca30b5f8cb0b72a4d806ea22a8748292b2a6d87e37e AS xfs-donor
RUN dnf -q -y --setopt=install_weak_deps=0 install xfsprogs && \
    mkdir -p /out/usr/local/bin /out/usr/lib64 && \
    cp -a /usr/sbin/mkfs.xfs /usr/sbin/xfs_growfs /usr/sbin/xfs_freeze \
          /usr/sbin/xfs_io /usr/sbin/xfs_info /usr/sbin/xfs_db /usr/sbin/xfs_repair \
          /out/usr/local/bin/ && \
    cp -a /usr/lib64/libinih.so.* /usr/lib64/liburcu.so.* \
          /usr/lib64/liburcu-common.so.* /usr/lib64/libedit.so.* \
          /out/usr/lib64/

# registry.access.redhat.com/hi/python:3.14-fips
FROM registry.access.redhat.com/hi/python:3.14-fips@sha256:6440a8d7c7f8ac513a4c061950ea883c0157e9f9a36e7aca4c3b723782fa7e04 AS runtime

FROM ${BASE_IMAGE} AS builder
WORKDIR $PYSETUP_PATH
COPY ./poetry.lock ./pyproject.toml ./
# Seed the venv with the base image's grpcio wheel; Poetry then sees the locked
# version installed and does not fetch the BoringSSL wheel from PyPI. (pip's
# direct_url.json for a local wheel would make Poetry treat it as a different
# source and reinstall it.)
RUN python3 -m venv "$VENV_PATH" && \
    pip install -q --no-deps /wheels/grpcio-*.whl && \
    rm -f "$VENV_PATH"/lib*/python3.*/site-packages/grpcio-*.dist-info/direct_url.json && \
    poetry install --only main,build --no-root

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

# Slim the venv: drop the stub generator (build group) and pip, and strip
# debug symbols from the extension modules.
# Then precompile bytecode: the runtime sets PYTHONDONTWRITEBYTECODE and Poetry
# does not compile, so without this every process compiles all sources at
# startup (e.g. kubernetes' 4MB core_v1_api.py) and the compiler's peak memory
# stays resident (~55MiB RSS per process). checked-hash keeps the .pyc valid
# regardless of the file mtimes after COPY.
# kubernetes>=37 also ships a full asyncio client (kubernetes/aio, ~38MiB of
# source, ~23MiB more once compiled); rawfile only uses the sync client and
# nothing else imports it, so drop it.
RUN cd $PYSETUP_PATH && \
    poetry sync --only main --no-root && \
    python -m pip uninstall -y pip setuptools wheel && \
    rm -rf "$VENV_PATH"/lib/python3.*/site-packages/kubernetes/aio && \
    find "$VENV_PATH" /rawfile -name '*.so*' -type f -exec strip --strip-unneeded '{}' + && \
    python -m compileall -q -j0 --invalidation-mode checked-hash "$VENV_PATH" /rawfile

# Assemble the runtime rootfs: the runtime image plus the OS tools rawfile
# needs (sh/bash, mount/umount/losetup/blkid/findmnt/blockdev/fsfreeze, ext4
# and btrfs tooling, cp --reflink) and Fedora's xfsprogs.
COPY --from=runtime / /rootfs
RUN dnf -q -y \
    --installroot=/rootfs \
    --releasever="$(. /etc/os-release && echo "$VERSION_ID")" \
    --setopt=install_weak_deps=0 \
    --setopt=tsflags=nodocs \
    install bash coreutils util-linux e2fsprogs btrfs-progs ncurses-libs && \
    dnf -q -y --installroot=/rootfs remove python3-pip && \
    dnf -q -y --installroot=/rootfs clean all && \
    rm -rf /rootfs/var/cache/dnf /rootfs/var/cache/libdnf5 /rootfs/var/log/dnf* /rootfs/var/log/hawkey* /rootfs/var/lib/dnf && \
    rm -rf /rootfs/usr/share/locale/* && \
    find /rootfs/usr/lib64/python3.* -name '*.opt-[12].pyc' -delete
COPY --from=xfs-donor /out/ /rootfs/

# Make sure the tools rawfile shells out to are present and resolvable (catches
# e.g. a Fedora-provided xfsprogs binary missing a shared library).
RUN chroot /rootfs /bin/bash -eu <<'EOF'
for b in bash mount umount losetup blkid findmnt blockdev fsfreeze cp \
         mkfs.ext4 resize2fs mkfs.btrfs btrfs \
         mkfs.xfs xfs_growfs xfs_freeze xfs_io xfs_info xfs_db xfs_repair; do
    path=$(command -v "$b") || { echo "missing: $b" >&2; exit 1; }
    if ldd "$path" 2>/dev/null | grep -q 'not found'; then
        echo "unresolved shared libraries in $path:" >&2
        ldd "$path" | grep 'not found' >&2
        exit 1
    fi
done
EOF

FROM scratch AS production
COPY --from=builder /rootfs/ /

ENV PATH=/opt/pysetup/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYSETUP_PATH=/opt/pysetup \
    VENV_PATH=/opt/pysetup/.venv

COPY --from=builder /opt/pysetup/.venv /opt/pysetup/.venv
COPY --from=builder /rawfile /rawfile
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Fail the build if FIPS mode is not active and enforced in the final image.
RUN python - <<'EOF'
import hashlib, ssl, sys
print(ssl.OPENSSL_VERSION)
try:
    hashlib.md5(b"x")
except ValueError:
    pass
else:
    sys.exit("MD5 usable for security: FIPS mode is NOT enforced")
hashlib.md5(b"x", usedforsecurity=False)
hashlib.sha256(b"x")
ssl.create_default_context()
import grpc
print("FIPS mode enforced; grpcio", grpc.__version__)
EOF

WORKDIR /rawfile

ARG IMAGE_TAG
ARG PROVISIONER_VERSION
ENV PROVISIONER_VERSION=${PROVISIONER_VERSION}

# rawfile mounts and loop-attaches devices; the pod runs privileged as root.
USER 0

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["csi-driver"]
