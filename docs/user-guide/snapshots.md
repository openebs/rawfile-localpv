# User Guide: Snapshots & Restore

RawFile LocalPV supports **block-level volume snapshots** through the standard
Kubernetes `VolumeSnapshot` API, including restoring snapshots into new PVCs.

## Before you begin

- Snapshots must be enabled in the chart (default): `capabilities.snapshots.enabled=true`.
- Snapshot CRDs installed (chart default): `crds.csi.volumeSnapshots.enabled=true`.
- A `VolumeSnapshotClass` exists — the chart creates `rawfile-localpv` by default:

```shell
kubectl get volumesnapshotclass rawfile-localpv
```

If you manage it yourself:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: rawfile-localpv
  # annotations:
  #   snapshot.storage.kubernetes.io/is-default-class: "true"
driver: rawfile.csi.openebs.io
deletionPolicy: Delete        # or Retain to keep snapshot data after object deletion
```

## Step 1 — Take a snapshot

Given an existing PVC `app-data`:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: app-data-snap-1
spec:
  volumeSnapshotClassName: rawfile-localpv
  source:
    persistentVolumeClaimName: app-data
```

```shell
kubectl apply -f snapshot.yaml
```

## Step 2 — Wait for the snapshot to be ready

```shell
kubectl get volumesnapshot app-data-snap-1
# NAME              READYTOUSE   SOURCEPVC   RESTORESIZE   SNAPSHOTCLASS     AGE
# app-data-snap-1   true         app-data    10Gi          rawfile-localpv   30s

kubectl get volumesnapshot app-data-snap-1 -o jsonpath='{.status.readyToUse}'
```

Snapshot creation runs as a persistent background task on the node that owns the
volume — it is retried automatically and survives driver restarts.

### Snapshotting in-use volumes

You can snapshot a volume while a pod is writing to it:

- If the pool's backing filesystem supports **copy-on-write** (e.g. btrfs, xfs with
  reflink — see
  [Storage Pools § CoW-capable pools](./storage-pools.md#copy-on-write-cow-capable-pools)
  for how to create one), the snapshot is cheap and consistent.
- Without CoW, enable `freezeFs: "true"` in the volume's StorageClass to briefly
  `fsfreeze` the filesystem during the snapshot for a crash-consistent image:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rawfile-freeze
provisioner: rawfile.csi.openebs.io
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
parameters:
  csi.storage.k8s.io/fstype: ext4
  copyOnWrite: "false"
  freezeFs: "true"
```

For application-level consistency (e.g. databases), quiesce the application or use its
native backup hooks before snapshotting.

## Step 3 — Restore into a new PVC

Create a new PVC with the snapshot as `dataSource`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data-restored
spec:
  storageClassName: rawfile-localpv
  accessModes: [ReadWriteOnce]
  dataSource:
    apiGroup: snapshot.storage.k8s.io
    kind: VolumeSnapshot
    name: app-data-snap-1
  resources:
    requests:
      storage: 10Gi        # must be >= the snapshot's restore size
```

```shell
kubectl apply -f restore.yaml
```

Then consume `app-data-restored` from a pod as usual. Notes:

- The restored volume is created on the **same node** as the snapshot (snapshots are
  node-local).
- Provisioning starts when a consuming pod is scheduled (`WaitForFirstConsumer`).
- The new PVC may use a different StorageClass, as long as it's a RawFile class.

### In-place "rollback" pattern

Kubernetes has no native in-place rollback. The common pattern:

```shell
# 1. Scale down the workload
kubectl scale deploy/app --replicas=0
# 2. Restore the snapshot into a new PVC (manifest above)
# 3. Point the workload at the new PVC and scale back up
kubectl scale deploy/app --replicas=1
# 4. Optionally delete the old PVC once verified
```

## Deleting snapshots

```shell
kubectl delete volumesnapshot app-data-snap-1
```

- With `deletionPolicy: Delete`, the on-disk snapshot data is removed.
- With `Retain`, the `VolumeSnapshotContent` (and data) remain and must be cleaned up
  manually.

> [!IMPORTANT]
> Before uninstalling the driver, delete all VolumeSnapshots (then PVCs, then PVs) to
> avoid leaked loop devices and mounts — see the
> [Install Guide](../install-guide.md#uninstall).

## Capacity considerations

- On non-CoW pools, a snapshot stores a full copy of the volume data — budget pool
  capacity accordingly.
- Restores allocate a new volume; check pool headroom with
  `rawfile_pool_remaining_capacity_bytes` (see [Monitoring](../monitoring.md)).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Snapshot never `readyToUse` | Check the node plugin logs on the volume's node; the create-snapshot task retries automatically. Also verify snapshot CRDs and the snapshotter sidecar are running. |
| `Snapshotting capabilities are disabled` | Set `capabilities.snapshots.enabled=true` in chart values and upgrade the release. |
| Restore PVC `Pending` | Needs a consuming pod (`WaitForFirstConsumer`) and enough free capacity on the **source's node**. |
| btrfs filesystem-level snapshots | Deprecated since v0.12.0 — existing ones can be deleted but new ones can't be created; block-level snapshots are the replacement. |

## Related guides

- [Cloning Volumes](./cloning.md) — direct PVC→PVC copies without a snapshot
- [Creating Volumes](./volumes.md)
- [StorageClass Configuration](../storageclass.md)
