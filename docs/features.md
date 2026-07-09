# Features

A detailed look at what RawFile LocalPV supports today. See the
[README](../README.md#features) for the at-a-glance checklist and
[StorageClass Configuration](./storageclass.md) for how to enable each behavior.

## Capability matrix

| Feature | Status | Notes |
|---|---|---|
| Dynamic provisioning | ✅ | `WaitForFirstConsumer`, strict topology, storage-capacity-aware scheduling |
| Direct I/O | ✅ | Loop devices opened with Direct I/O — near-zero overhead vs. the raw disk |
| Enforced size limits | ✅ | Enforced by the kernel via the backing file / filesystem size |
| Access mode `ReadWriteOnce` | ✅ | Only supported mode (`ReadWriteOncePod` planned) |
| `ReadOnlyMany` / `ReadWriteMany` | ❌ | Not possible for node-local volumes |
| Volume mode `Filesystem` | ✅ | ext4 / xfs / btrfs |
| Volume mode `Block` | ✅ | Raw loop device handed to the pod (`readOnly` attribute not yet honored) |
| Thick provisioning | ✅ | Default; full preallocation, no overprovisioning |
| Thin provisioning | ✅ | Sparse backing files; enables overprovisioning |
| Online expansion | ✅ | ext4, xfs, btrfs — no remount/restart |
| Online/offline shrinking | ❌ | Not supported |
| Volume snapshots | ✅ | Block-level, node-local (distributed snapshotting); btrfs FS-level snapshots deprecated |
| Volume cloning | ✅ / 🚧 | Same-node cloning supported; cross-node in progress |
| Storage pools | ✅ | Multiple named pools per node, capacity reservation, per-SC pool selection |
| Volume metrics | ✅ | Prometheus, per node / pool / volume — see [Monitoring](./monitoring.md) |
| REST API | ✅ (optional) | Nodes/pools/volumes/tasks introspection |
| Capacity tracking | ✅ | `CSIStorageCapacity` published per node/pool |
| fsGroup support | ✅ | `fsGroupPolicy: File` |

## Feature notes

### Dynamic provisioning & scheduling

Volumes are created on the node where the first consumer pod is scheduled. The driver
publishes per-node free capacity so the Kubernetes scheduler avoids nodes that can't fit
a volume. The resulting PV is pinned to that node via the `hostname` topology key.

### Thick vs. thin provisioning

- **Thick (default)**: the backing file is fully allocated at creation. Capacity
  accounting is exact and overprovisioning is impossible.
- **Thin**: the backing file is sparse and grows on write. Since v0.13.0, capacity
  calculations use actually-allocated blocks, so thin volumes can overcommit the pool.
  This is powerful but requires monitoring pool utilization.

Set via the `thinProvision` StorageClass parameter.

### Filesystems

Supported fsTypes: **ext4** (default), **xfs**, **btrfs**. Each volume gets its own
filesystem, so different volumes may use different filesystems and custom format
(`formatOptions`) / mount (`mountOptions`) options — independent of what the host node
uses. Filesystems are created lazily at first stage and repaired (fsck) as needed on
subsequent stages.

### Online expansion

Grow the PVC and the driver grows the backing file, the loop device and the filesystem
online. The request is routed from the controller to the owning node over the internal
gRPC channel. Unstaged block-mode volumes don't need (and skip) node expansion.

### Snapshots

Block-level snapshots via the standard `VolumeSnapshot` API. Highlights:

- **Distributed snapshotting**: the CSI snapshotter runs alongside each node plugin, so
  snapshots are taken where the data lives.
- **CoW-aware**: on pools whose backing filesystem supports copy-on-write/reflinks,
  snapshots are cheap; otherwise data is copied.
- **`freezeFs`**: optionally freeze the filesystem of an in-use volume during
  snapshotting for crash-consistency when CoW is unavailable.
- Snapshot creation runs as a persistent, retried background task
  ([Task Manager](./design/taskmanager.md)) that survives driver restarts.

### Cloning & restore

New PVCs can source from a `VolumeSnapshot` or directly from another PVC. Both happen on
the node that holds the source, and cloning requires roughly **3× the volume size** of
free pool capacity during the copy.

### Storage pools

Multiple independent pools per node (e.g. an NVMe pool and an HDD pool), each on its own
backing filesystem, each with its own capacity reservation policy. StorageClasses select
a pool via the `storagePool` parameter, enabling storage tiering. See
[StorageClass Configuration](./storageclass.md#storagepool).

### Observability

- Prometheus metrics on every node plugin (`metrics.port`, default 9100), with an
  optional `ServiceMonitor`.
- Structured JSON (or pretty) logs with request-level gRPC logging; log level tunable
  down to `TRACE`.
- Optional REST API server for cluster-wide nodes/pools/volumes/tasks inspection.

### Reliability

- **Task manager**: long operations (volume creation, snapshots) run as persisted,
  retryable tasks; crashes and restarts recover in-flight work.
- **Preflight checks**: the node plugin validates pool/metadata directories, uniqueness
  of backing filesystems, and migrates metadata layouts on startup.
- **Garbage collection**: a `gc` subcommand detects orphaned volumes (dry-run executed at
  each node-plugin startup).
- **Graceful shutdown**: gRPC servers and background tasks drain with a grace period on
  termination.

### Security

- Internal node-to-node/controller-to-node gRPC is token-authenticated
  (chart `auth.*` values; token auto-generated if not provided).
- Data and metadata directories are created with restrictive permissions (`0700`).

## Current limitations

- Volumes are strictly node-local — no replication; node loss means data loss for
  volumes on that node.
- `ReadWriteOnce` only; `readOnly` attribute of block PVCs not honored.
- No shrinking.
- Cross-node cloning not yet available.
- Pre-v1: Helm API and StorageClass parameters may still see breaking changes — read the
  [install guide's upgrade notes](./install-guide.md#upgrade) before upgrading.
