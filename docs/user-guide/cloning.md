# User Guide: Cloning Volumes

Cloning creates a new PVC that starts as an exact copy of an existing PVC, without an
intermediate snapshot object.

## Before you begin

- Cloning uses the snapshotting machinery, so it must be enabled (chart default):
  `capabilities.snapshots.enabled=true`.
- Clones are created on the **same node** as the source volume (cross-node cloning is
  in progress).
- The source volume's pool needs roughly **3× the volume size** of free capacity while
  the clone is being materialized.

## Step 1 — Clone an existing PVC

Given a source PVC `app-data`, create a new PVC with a `dataSource` of kind
`PersistentVolumeClaim`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data-clone
spec:
  storageClassName: rawfile-localpv     # must be a RawFile class
  accessModes: [ReadWriteOnce]
  dataSource:
    kind: PersistentVolumeClaim
    name: app-data                      # source PVC (same namespace)
  resources:
    requests:
      storage: 10Gi                     # must be >= source size
```

```shell
kubectl apply -f clone.yaml
```

## Step 2 — Consume the clone

As with any RawFile PVC, provisioning starts when a pod uses it:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-clone-consumer
spec:
  containers:
    - name: app
      image: busybox
      command: ["sh", "-c", "sleep infinity"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: app-data-clone
```

```shell
kubectl get pvc app-data-clone -w      # wait for Bound
kubectl exec app-clone-consumer -- ls /data
```

The clone is fully independent of the source after creation — changes to one do not
affect the other.

## Clone vs. snapshot+restore

| | Clone (`dataSource: PVC`) | Snapshot + restore |
|---|---|---|
| Point-in-time copy kept around | ❌ one-shot copy | ✅ snapshot object persists |
| Extra API objects | none | `VolumeSnapshot` + `VolumeSnapshotClass` |
| Use case | duplicate an environment, fork test data | backup/rollback points, repeated restores |

Both are node-local and use the same underlying copy mechanism (cheap on CoW-capable
pool filesystems, full copy otherwise).

## Consistency

Cloning a volume that is actively being written gives a crash-consistent copy at best.
For consistent clones of busy volumes:

- use a StorageClass with `freezeFs: "true"` (filesystem is frozen during the copy), or
- use a Storage Pool with a CoW-capable filesystem (e.g. XFS with reflink, btrfs) — see
  [Storage Pools § CoW-capable pools](./storage-pools.md#copy-on-write-cow-capable-pools)
  for how to create one.

> [!WARNING]
> With `freezeFs: "true"` on a **non-CoW** pool, the volume's filesystem stays frozen
> for the **entire duration of the data copy** — all writes to the volume block until
> the clone completes, which can take a long time for large volumes. Prefer a
> CoW-capable pool filesystem, where the copy is nearly instantaneous.

If none of these are available, the clone will get rejected and scale down will be required in order to clone the volume

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Insufficient disk space (Cloning a volume requires at least 3× the volume size)` | Free up pool capacity on the source's node, or grow the underlying disk. |
| Clone PVC `Pending` | Needs a consuming pod (`WaitForFirstConsumer`); check `kubectl describe pvc` events. |
| `Snapshotting capabilities are disabled` | Enable `capabilities.snapshots.enabled=true` in chart values and upgrade. |
| Clone must land on a different node | Not yet supported — cross-node cloning is in progress. |

## Related guides

- [Snapshots & Restore](./snapshots.md)
- [Creating Volumes](./volumes.md)
