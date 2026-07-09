# Architecture

This document describes how OpenEBS LocalPV RawFile works internally: its components,
how volumes are provisioned, and how data flows through the system.

## The Core Idea

Instead of bind-mounting a host directory into pods (like HostPath / LocalPV-HostPath),
RawFile creates a **raw extent file** on a node's filesystem for every volume, attaches it
to a **Linux loop device**, and (for `Filesystem` volume mode) formats it with its own
filesystem:

```
   Pod
    │  volumeMounts
    ▼
  Mountpoint  ◄─── mkfs (ext4 / xfs / btrfs)
    │
  /dev/loopN  ◄─── losetup (Direct I/O enabled)
    │
  <pool-path>/<pv-name>/disk.img   (raw extent file — thick or thin/sparse)
    │
  Node's backing filesystem (a storage pool)
```

Because every volume is a real (emulated) block device with its own filesystem:

- Size limits are enforced by the kernel on each volume's own filesystem, rather
  than by quotas or accounting on the host's shared filesystem.
- Usage can be measured in `O(1)` via `statvfs`/`df`, per volume.
- Each volume can use a different filesystem and format/mount options.
- Direct I/O through the loop device keeps performance close to bare-metal.

## Components

### Deployed by the Helm chart

| Component | Kind | Purpose |
|---|---|---|
| **Node plugin** | DaemonSet | Runs on every eligible node. Implements the CSI Node service (stage/publish/expand), and — because provisioning, snapshots and clones all operate on data local to a node — also the CSI Controller service for those operations on that node. Serves per-node metrics and an internal gRPC service. |
| **Controller** | Deployment | Implements cluster-wide controller operations that must be routed to the right node, most notably volume expansion (`csi-resizer` sidecar attaches here). Deployed only when `capabilities.resize.enabled=true`. |
| **API server** | Deployment (optional) | FastAPI REST service exposing cluster-wide node/pool/volume/task information. Deployed when `capabilities.apiServer.enabled=true`. |
| **CSIDriver object** | `CSIDriver` | Registered as `rawfile.csi.openebs.io` with `attachRequired: false`, `podInfoOnMount: true`, `fsGroupPolicy: File`, `storageCapacity: true`. |
| **StorageClass(es)** / **VolumeSnapshotClass(es)** | Cluster objects | Created from `storageClasses` / `snapshotClasses` chart values. |

### CSI sidecars

The node plugin pod carries the sidecars, because provisioning and snapshotting are
node-local:

- `csi-provisioner` (runs in **strict topology** mode with storage-capacity tracking)
- `csi-snapshotter` + `snapshot-controller` (when snapshots are enabled)
- `csi-node-driver-registrar`

The controller pod carries `csi-resizer`.

### Internal gRPC service

Node plugins expose an **internal gRPC server** (default port `4500`) used for
node-to-node and controller-to-node communication — e.g. the controller forwards
`ControllerExpandVolume` to the node that owns the volume, and the API server gathers
pool statistics. Requests are authenticated with a shared token (chart `auth.*` values,
stored in a Secret) enforced by a signature interceptor.

The driver discovers node IPs by watching the node-plugin DaemonSet pods
(`orchestrator/k8s.py`), maintaining a node-name → IP mapping.

## Topology & Scheduling

Every volume is pinned to a single node using the topology key `hostname`. The flow:

1. StorageClasses use `volumeBindingMode: WaitForFirstConsumer`, so binding waits until
   a pod is scheduled.
2. `csi-provisioner` runs with strict topology: the scheduler's choice becomes the
   `preferred` topology in `CreateVolume`.
3. The driver publishes **storage capacity** (`CSIStorageCapacity` objects, polled every
   `capacityPollInterval`) so the scheduler avoids nodes without enough free pool space.
4. The resulting PV carries a node affinity for that node; the workload is thereafter
   co-scheduled with its data (like any local PV).

## Storage Pools

A **storage pool** is a named directory on each node under which volumes are created.
Pools are defined in the chart (`node.storagePools`), and every node plugin validates:

- pool names are DNS-compatible, 3–63 characters;
- pool paths are unique **and live on distinct backing filesystems**;
- a `node.defaultPool` exists among the configured pools.

Each pool supports capacity reservation (`reservedCapacity` as bytes or a percentage,
with `plain` or `subtract-from-total` semantics — see the
[StorageClass guide](./storageclass.md#storagepool)). Capacity accounting counts
**physical (allocated) blocks** of backing files, which allows overprovisioning with
thin volumes.

Volume **metadata** (JSON schema per volume, plus the task store `tasks.json`) lives in a
separate metadata directory (`node.metadataDirPath`, default
`/var/local/openebs/rawfile/<release>/meta`).

## Volume Lifecycle

### Provisioning (`CreateVolume`)

1. `csi-provisioner` calls `CreateVolume` on the node plugin of the scheduled node.
2. Parameters from the StorageClass are parsed (`thinProvision`, `formatOptions`,
   `copyOnWrite`, `freezeFs`, `storagePool`, fsType).
3. Pool capacity is checked (cloning requires ≥ 3× the volume size).
4. The actual creation runs asynchronously through the [Task Manager](./design/taskmanager.md):
   allocate the backing file (thick `fallocate`-style or thin/sparse), apply CoW
   attributes, and — if the volume has a content source — populate it from a snapshot or
   another volume.
5. `CreateVolume` waits (up to 30s) for the volume to be marked ready; otherwise returns
   `DEADLINE_EXCEEDED` and the CO retries while the task keeps running.

### Staging & Publishing (node)

The `Bd2FsNodeServicer` ("**b**lock **d**evice **2** **f**ile**s**ystem") wraps the raw
block-device servicer:

- **Stage**: attach the backing file to a loop device; for `Filesystem` mode, create the
  filesystem on first use (honoring fsType and `formatOptions`), run fsck/repair as
  needed, then mount at the staging path.
- **Publish**: bind-mount the staged mount (or expose the loop device directly for
  `Block` mode) into the pod. Per-volume locks (`VolLock`) serialize concurrent
  operations on the same volume.
- **Unpublish/Unstage**: unmount and detach loop devices.

### Expansion

`ControllerExpandVolume` reaches the controller Deployment, which looks up the node
owning the volume and forwards the request over internal gRPC. The node grows the
backing file, resizes the loop device, and (online) grows the filesystem
(ext4/xfs/btrfs). Unstaged block volumes skip node expansion.

### Snapshots & Clones

Snapshots are **block-level** and node-local ("distributed snapshotting" — the
external-snapshotter runs on each node). Creating a snapshot copies/materializes the
volume state; `freezeFs` can be enabled to `fsfreeze` in-use volumes when CoW is not
available, while on CoW-capable filesystems (e.g. btrfs, xfs with reflink) copies are
cheap. Clones (`PVC dataSource`) restore from a volume/snapshot on the **same node**
(cross-node cloning is in progress). Filesystem-level btrfs snapshots are deprecated.

### Deletion & GC

`DeleteVolume` removes the backing file and metadata, failing with
`FAILED_PRECONDITION` if the volume is in use. On node-plugin startup a garbage
collection pass (`gc` subcommand, dry-run at boot) detects and reports orphaned
volumes; metadata migration from older layouts also happens at startup
(preflight checks).

## Process & Configuration Model

All components run from a single Python entrypoint (`rawfile.py`) with
pydantic-settings based CLI/env configuration (`config/model.py`):

- `csi-driver` subcommand — `plugin_type: node | controller`, endpoint, storage pools,
  default fs, capability toggles (`resize`, `snapshots`), metrics port, gRPC workers.
- `api` subcommand — REST API server host/port/workers.
- `gc` subcommand — offline volume garbage collection (`--dry-run` by default).

Common settings: `namespace`, `log_level` (TRACE…CRITICAL), `log_format`
(`json`/`pretty`), analytics (`ga_*`), internal gRPC port/signature, node DaemonSet
name for discovery. Environment variables use `__` as a nesting delimiter.

## REST API Server (optional)

A FastAPI-based REST API server is provided for cluster-wide introspection of nodes,
pools, volumes and background tasks. It aggregates data by fanning out over the
internal gRPC service to each node plugin.

The OpenAPI spec is available at `/openapi.json` and the Swagger UI at `/docs`.
Also It is available at Release files on the [Github Releases](https://github.com/openebs/rawfile-localpv/releases)
and generated after each release.

## Observability

- Structured logging (JSON or pretty) with per-request gRPC logging.
- Prometheus metrics per node, pool and volume — see [Monitoring](./monitoring.md).
- Optional anonymous usage analytics (Google Analytics), controlled via
  `analytics.enabled` in the chart.
