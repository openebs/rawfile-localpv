# User Guide: Storage Pools

Storage pools let each node offer one or more named storage locations (e.g. an NVMe
pool and an HDD pool), each backed by its own filesystem, with independent capacity
reservations. StorageClasses select a pool via the `storagePool` parameter, enabling
storage tiering.

## Configuring pools (Helm values)

Pools are defined per-release in the chart under `node.storagePools`, together with a
`node.defaultPool`:

```yaml
# values.yaml
node:
  defaultPool: hdd
  storagePools:
    hdd:
      path: /var/local/openebs/rawfile/hdd/
      # keep 10% of the backing disk free for the OS and other tenants
      reservedCapacity: "10%"
      reservedCapacityMode: plain
    nvme:
      path: /mnt/nvme/rawfile/
      # this pool may use at most (disk size - 20GiB)
      reservedCapacity: 20GiB
      reservedCapacityMode: subtract-from-total
```

```shell
helm upgrade rawfile-localpv rawfile-localpv/rawfile-localpv \
  -n openebs -f values.yaml
```

### Rules and validation

The node plugin validates pools at startup:

| Rule | Detail |
|---|---|
| Name | DNS-compatible, 3–63 characters |
| Path | Must exist/be creatable, unique per node |
| Backing filesystem | Each pool must live on a **distinct filesystem** — two pools on the same device are rejected |
| Default pool | `node.defaultPool` is required and must name one of the pools |

> [!NOTE]
> `node.dataDirPath` and the top-level `reservedCapacity` are **deprecated**. If you
> still use them, a pool named `data-dir` is auto-created; migrate to
> `node.storagePools` (see the
> [v0.13.0 upgrade notes](../install-guide.md#upgrading-to-v0130)).

### Reserved capacity semantics

`reservedCapacity` accepts a percentage (`"10%"`) or byte size (`20GiB`, `100GB`, …):

- **`plain`** (default): reserve space for *everything else but this pool* — the pool
  can grow until `reservedCapacity` is left free on the backing filesystem.
- **`subtract-from-total`**: cap the pool at `total - reservedCapacity` — effectively
  "this pool may grow up to that much".

Example on a 1TiB disk with `reservedCapacity: 100GiB`:

| Mode | Pool capacity |
|---|---|
| `plain` | grows until 100GiB is left free (≈ 924GiB usable) |
| `subtract-from-total` | capped at 1TiB − 100GiB = 924GiB… but expressed as "up to 100GiB less than the disk" |

## Copy-on-write (CoW) capable pools

Snapshots and clones are **cheap and consistent** when the pool's **backing
filesystem** (the filesystem hosting the pool path — not the filesystem inside the
volumes) supports copy-on-write/reflinks:

- **btrfs**: CoW-capable out of the box.
- **XFS**: must be created with reflink support enabled:

  ```shell
  mkfs.xfs -m reflink=1 /dev/<disk>
  ```

  Reflink is the default on recent `xfsprogs` (≥ 5.1); verify an existing filesystem
  with `xfs_info <mountpoint> | grep reflink` (`reflink=1`).
- **ext4**: no reflink support — snapshots/clones on ext4-backed pools perform a full
  data copy (consider `freezeFs: "true"` for consistency of in-use volumes).

The driver autodetects CoW support per pool; the REST API (`GET /v1/nodes/`) and
node logs report it per pool.

## Using pools from StorageClasses

Create one StorageClass per tier:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rawfile-nvme
provisioner: rawfile.csi.openebs.io
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
parameters:
  csi.storage.k8s.io/fstype: xfs
  storagePool: nvme
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rawfile-hdd
provisioner: rawfile.csi.openebs.io
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
parameters:
  csi.storage.k8s.io/fstype: ext4
  storagePool: hdd
```

Or via chart values:

```yaml
storageClasses:
  - name: rawfile-nvme
    enabled: true
    volumeBindingMode: WaitForFirstConsumer
    allowVolumeExpansion: true
    reclaimPolicy: Delete
    fsType: xfs
    storagePool: nvme
  - name: rawfile-hdd
    enabled: true
    volumeBindingMode: WaitForFirstConsumer
    allowVolumeExpansion: true
    reclaimPolicy: Delete
    fsType: ext4
    storagePool: hdd
```

Then workloads simply pick the class:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fast-db-data
spec:
  storageClassName: rawfile-nvme
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 50Gi
```

A StorageClass without `storagePool` uses the node's `defaultPool`. If the named pool
doesn't exist on a node, that node publishes **no storage capacity** for the class
(`GetCapacity` fails with `Invalid storage pool` — visible in the `csi-provisioner`
sidecar logs), so pods consuming such a PVC stay `Pending` with
`did not have enough free storage`. Keep pool definitions consistent across nodes
(or constrain workloads with node selectors).

## Observing pools

- **Metrics** (per node & pool): `rawfile_pool_capacity_bytes`,
  `rawfile_pool_remaining_capacity_bytes`, `rawfile_pool_reserved_capacity_bytes`,
  `rawfile_pool_volume_count`, and more — see [Monitoring](../monitoring.md).
- **Scheduler view**: `kubectl get csistoragecapacities -A` shows the per-node capacity
  published for scheduling.
- **REST API** (if enabled): `GET /v1/nodes/` lists every node's pools with capacity,
  reservation, and CoW support.

## Changing pool configuration

- **Adding a pool**: add it to `node.storagePools` and `helm upgrade`; node plugins
  pick it up on restart.
- **Changing `reservedCapacity`**: safe; only affects capacity accounting for new
  provisioning.
- **Moving/renaming a pool**: not supported in place — existing volumes reference their
  pool. Drain volumes first (delete/migrate PVCs), then change the configuration.
- **Removing a pool**: ensure no volumes remain in it before removing it from values.

## Related guides

- [Creating Volumes](./volumes.md)
- [StorageClass Configuration reference](../storageclass.md)
- [Architecture § Storage Pools](../architecture.md#storage-pools)
