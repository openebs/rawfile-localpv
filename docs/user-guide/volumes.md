# User Guide: Creating and Configuring Volumes

This guide covers everything about provisioning RawFile LocalPV volumes: setting up a
StorageClass, creating PVCs in `Filesystem` and `Block` mode, customizing filesystem
behavior, and deleting volumes.

## Before you begin

- The driver is installed — see the [Install Guide](../install-guide.md).
- A StorageClass exists. The chart creates `rawfile-localpv` by default:

```shell
kubectl get sc rawfile-localpv
```

## Step 1 — Choose or create a StorageClass

The default chart-managed StorageClass works out of the box (ext4, thick-provisioned,
default pool). To customize behavior, create your own class — the full parameter
reference is in [StorageClass Configuration](../storageclass.md):

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rawfile-custom
provisioner: rawfile.csi.openebs.io       # chart value `provisionerName`
reclaimPolicy: Delete                     # or Retain
volumeBindingMode: WaitForFirstConsumer   # required — do not use Immediate
allowVolumeExpansion: true
mountOptions:
  - noatime
parameters:
  csi.storage.k8s.io/fstype: xfs          # ext4 (default) | xfs | btrfs
  thinProvision: "false"                  # "true" = sparse file, allows overprovision
  formatOptions: ""                       # extra mkfs flags, e.g. "-I 256"
  copyOnWrite: "false"                    # CoW attribute of the backing file
  freezeFs: "false"                       # fsfreeze during snapshots of in-use volumes
  # storagePool: nvme                     # omit the key entirely to use the node's
                                          # default pool — an empty string ("") is
                                          # rejected as an invalid pool name
```

```shell
kubectl apply -f storageclass.yaml
```

> [!IMPORTANT]
> Always use `volumeBindingMode: WaitForFirstConsumer`. The driver provisions volumes
> on the node chosen by the scheduler; `Immediate` binding fails with
> "No preferred topology set".

### Common configurations

| Goal | Parameters |
|---|---|
| Database volume (max write perf) | `copyOnWrite: "false"`, `fsType: ext4` or `xfs`, `mountOptions: [noatime]` |
| Space-efficient dev/test volumes | `thinProvision: "true"` |
| Snapshot-heavy workload | pool on a CoW filesystem, or `freezeFs: "true"` |
| Fast tier | `storagePool: nvme` (see [Storage Pools guide](./storage-pools.md)) |

## Step 2 — Create a PersistentVolumeClaim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
spec:
  storageClassName: rawfile-custom
  accessModes:
    - ReadWriteOnce            # the only supported access mode
  resources:
    requests:
      storage: 10Gi
```

```shell
kubectl apply -f pvc.yaml
kubectl get pvc app-data
```

The PVC stays **`Pending`** — that's normal. With `WaitForFirstConsumer`, provisioning
starts only when a pod that uses the PVC is scheduled.

## Step 3 — Consume the volume in a workload

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
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
        claimName: app-data
```

Once the pod is scheduled:

1. The scheduler picks a node with enough free pool capacity (capacity-aware).
2. The driver creates the backing file in the pool, attaches a loop device, formats it
   with the configured filesystem, and mounts it into the pod.
3. The PV gets a node affinity — the workload will always run on that node from now on.

Verify:

```shell
kubectl get pvc app-data                     # should be Bound
kubectl exec app -- df -hT /data             # per-volume filesystem, exact size limit
```

## Raw Block volumes

To hand the pod a raw block device (no filesystem — useful for databases or systems
that manage their own storage format), set `volumeMode: Block`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-block
spec:
  storageClassName: rawfile-custom
  accessModes: [ReadWriteOnce]
  volumeMode: Block
  resources:
    requests:
      storage: 10Gi
```

Consume it with `volumeDevices` instead of `volumeMounts`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-block-consumer
spec:
  containers:
    - name: app
      image: busybox
      command: ["sh", "-c", "sleep infinity"]
      volumeDevices:
        - name: data
          devicePath: /dev/xvda
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: app-block
```

Notes:

- `fsType`, `formatOptions` and `mountOptions` are ignored in Block mode.
- The `readOnly` attribute of block PVCs is not currently honored.

## Selecting a storage pool

If your nodes define multiple pools (e.g. `nvme` and `hdd`), point a StorageClass at a
specific pool with the `storagePool` parameter. Omitting it uses the node's default
pool. See the [Storage Pools guide](./storage-pools.md).

## Thin vs. thick provisioning

- **Thick (default, `thinProvision: "false"`)** — full allocation up front. What you
  request is what's consumed; no overprovisioning possible.
- **Thin (`thinProvision: "true"`)** — sparse backing file that grows on write. Lets you
  overcommit the pool, but you must monitor real usage
  (`rawfile_pool_remaining_capacity_bytes`) to avoid running the pool out of space —
  writes to any volume fail if the backing filesystem fills up.

## Deleting volumes

1. Delete the workload(s) using the PVC. Deletion fails with `Volume in use` while a
   pod still mounts it.
2. Delete the PVC:

```shell
kubectl delete pvc app-data
```

With `reclaimPolicy: Delete`, the PV, backing file and metadata are removed from the
node. With `Retain`, the PV and data remain until you delete the PV manually.

> [!WARNING]
> Delete any `VolumeSnapshot`s of a volume before deleting the volume itself if you
> intend to fully reclaim space — see [Snapshots & Restore](./snapshots.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| PVC `Pending` forever | Is a pod consuming it? Enough capacity? `kubectl get csistoragecapacities -A`; `kubectl describe pvc <name>` for events. |
| `Invalid storage pool` error | The `storagePool` parameter doesn't match a configured pool name on the node. |
| Pod stuck `ContainerCreating` | Check node plugin logs: `kubectl -n openebs logs ds/<release>-node -c csi-driver`. |
| Volume created but wrong filesystem | fsType applies at first format only; recreate the volume to change it. |

## Related guides

- [Resizing Volumes](./resize.md)
- [Snapshots & Restore](./snapshots.md)
- [Cloning Volumes](./cloning.md)
- [Storage Pools](./storage-pools.md)
- [StorageClass Configuration reference](../storageclass.md)
