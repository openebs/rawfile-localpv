# StorageClass Configuration Reference

All per-volume behavior of RawFile LocalPV is configured through the **StorageClass**.
The Helm chart can generate StorageClasses for you (`storageClasses` value — one entry
per class), or you can write them by hand using the provisioner name
`rawfile.csi.openebs.io` (chart value `provisionerName`).

## Full example

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rawfile-fast
provisioner: rawfile.csi.openebs.io
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
mountOptions:
  - noatime
parameters:
  csi.storage.k8s.io/fstype: xfs
  thinProvision: "true"
  formatOptions: "-i maxpct=10"
  copyOnWrite: "true"
  freezeFs: "false"
  storagePool: nvme
```

Equivalent via chart values:

```yaml
storageClasses:
  - name: rawfile-fast
    enabled: true
    volumeBindingMode: WaitForFirstConsumer
    isDefault: false
    allowVolumeExpansion: true
    reclaimPolicy: Delete
    fsType: xfs
    thinProvision: "true"
    mountOptions: ["noatime"]
    formatOptions: ["-i", "maxpct=10"]
    copyOnWrite: "true"
    freezeFs: "false"
    storagePool: nvme
```

> [!NOTE]
> Parameter keys are matched case-insensitively by the driver. Values must be strings
> (quote booleans). Boolean values accept the usual truthy/falsy spellings
> (`true`/`false`, `yes`/`no`, `1`/`0`).

## Parameters (`parameters:`)

### `csi.storage.k8s.io/fstype`

Filesystem created on the volume for `Filesystem` volume mode.

- **Supported**: `ext4` (default), `xfs`, `btrfs`
- If unspecified, falls back to the node plugin's `defaultFs` (chart value
  `node.defaultFs`, default `ext4`).
- Ignored for `volumeMode: Block` PVCs.

### `thinProvision`

- **Values**: `"true"` / `"false"` — **default `"false"`** (thick)
- Thick volumes preallocate the full backing file at creation time; the space is
  counted against pool capacity up front and cannot be overprovisioned.
- Thin volumes are created **sparse**: blocks are allocated on write. Capacity
  accounting uses physically allocated blocks, so thin volumes **enable
  overprovisioning** — the pool may run out of real space if overcommitted. Monitor
  `rawfile_pool_remaining_capacity_bytes` when using thin provisioning.

### `formatOptions`

- **Value**: space-separated string of extra flags passed to `mkfs.<fstype>` when the
  filesystem is first created (e.g. `"-I 256"` for ext4, `"-i maxpct=10"` for xfs).
  Note these apply to the filesystem created **inside the volume** — options for the
  pool's backing filesystem (e.g. reflink support for CoW) must be set when creating
  that filesystem on the host; see
  [Storage Pools § CoW-capable pools](./user-guide/storage-pools.md#copy-on-write-cow-capable-pools).
- In chart values this is a **list** that gets joined with spaces.
- Applied only at first format (volume creation), not on subsequent mounts.

### `copyOnWrite`

- **Values**: `"true"` / `"false"` / unset
- Controls the copy-on-write attribute of the volume's backing file on the pool's
  filesystem.
- **Unset (writing your own SC)**: the driver autodetects CoW support of each pool's
  backing filesystem and applies it accordingly. The chart's generated StorageClasses
  default this to `"false"` unless you set the `copyOnWrite` value.
- CoW (available e.g. on btrfs or xfs-with-reflink pool filesystems — see
  [Storage Pools § CoW-capable pools](./user-guide/storage-pools.md#copy-on-write-cow-capable-pools))
  makes snapshots
  and clones cheap; disabling CoW (`nodatacow`-style) can improve write performance for
  workloads like databases.

### `freezeFs`

- **Values**: `"true"` / `"false"` — **default `"false"`**
- When enabled, the volume's filesystem is frozen (`fsfreeze`) while a snapshot of an
  **in-use** volume is taken, guaranteeing a crash-consistent image. Mainly useful when
  the pool's backing filesystem does **not** support CoW (where snapshots would
  otherwise copy live data).
- Expect a brief I/O pause on the volume during snapshot creation.

### `storagePool`

- **Value**: name of one of the storage pools configured on the nodes
  (chart value `node.storagePools`).
- **Default**: the node plugin's `defaultPool` (chart value `node.defaultPool`).
- Provisioning fails with `INVALID_ARGUMENT` if the named pool doesn't exist on the
  selected node. Use multiple StorageClasses pointing at different pools to offer
  storage tiers (e.g. `nvme` vs `hdd`):

```yaml
node:
  defaultPool: hdd
  storagePools:
    hdd:
      path: /var/local/openebs/rawfile/hdd/
      reservedCapacity: "10%"
    nvme:
      path: /mnt/nvme/rawfile/
      reservedCapacity: 20GiB
      reservedCapacityMode: subtract-from-total
```

Pool notes:

- Pool names must be DNS-compatible, 3–63 characters.
- Each pool path must live on a **distinct backing filesystem** per node.
- `reservedCapacity` accepts a percentage (`"10%"`) or a byte size (`20GiB`).
- `reservedCapacityMode`:
  - `plain` (default): the reservation is held back from the pool — the pool can grow
    until `reservedCapacity` is left free ("reserve for everything but this pool").
  - `subtract-from-total`: the pool may use at most `total - reservedCapacity`…
    effectively "this pool may grow up to `reservedCapacity` less than the disk".

## Standard StorageClass fields

| Field | Recommended | Notes |
|---|---|---|
| `volumeBindingMode` | `WaitForFirstConsumer` | **Required in practice.** The driver needs the scheduler's node choice (strict topology); `Immediate` binding will fail with "No preferred topology set". |
| `allowVolumeExpansion` | `true` | Enables online expansion (ext4/xfs/btrfs). Requires the controller component (`capabilities.resize.enabled=true`). |
| `reclaimPolicy` | `Delete` or `Retain` | `Delete` removes the backing file when the PV is released. |
| `mountOptions` | as needed | Passed through to the volume's mount (e.g. `noatime`, `discard`). |
| `parameters` | see above | Driver-specific behavior. |

## VolumeSnapshotClass

Snapshots use a `VolumeSnapshotClass` (chart value `snapshotClasses`):

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: rawfile-localpv
driver: rawfile.csi.openebs.io
deletionPolicy: Delete   # or Retain
```

There are no driver-specific snapshot-class parameters; snapshot behavior
(`freezeFs`, `copyOnWrite`) is inherited from the volume's StorageClass.

## PVC-level knobs

| PVC field | Support |
|---|---|
| `accessModes` | `ReadWriteOnce` only |
| `volumeMode: Filesystem` | ✅ default |
| `volumeMode: Block` | ✅ raw loop device exposed to the pod (the `readOnly` attribute is not currently honored) |
| `dataSource` (snapshot) | ✅ same-node restore |
| `dataSource` (PVC clone) | ✅ same-node clone; needs ~3× volume size free during copy |
| shrink (`storage` decrease) | ❌ not supported |
