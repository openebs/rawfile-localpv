# User Guide: Resizing (Expanding) Volumes

RawFile LocalPV supports **online expansion** of volumes — the backing file, loop
device and filesystem are grown live, with no pod restart or remount. Shrinking is not
supported.

## Before you begin

- Resize must be enabled in the chart (default): `capabilities.resize.enabled=true`
  (this deploys the controller component with the `csi-resizer` sidecar).
- The StorageClass must allow expansion:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rawfile-localpv
provisioner: rawfile.csi.openebs.io
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
allowVolumeExpansion: true      # ← required for resize
parameters:
  csi.storage.k8s.io/fstype: ext4
```

- Online filesystem growth works for `ext4`, `xfs` and `btrfs` (all supported fsTypes).
- Enough free capacity must exist in the volume's storage pool on its node.

## Step 1 — Increase the PVC size

Edit the PVC's `spec.resources.requests.storage` to the new (larger) size:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
spec:
  storageClassName: rawfile-localpv
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 20Gi        # was 10Gi
```

```shell
kubectl apply -f pvc.yaml
```

Or patch in place:

```shell
kubectl patch pvc app-data \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

## Step 2 — Watch the expansion complete

```shell
kubectl get pvc app-data -w
# NAME       STATUS   VOLUME      CAPACITY   ACCESS MODES   STORAGECLASS
# app-data   Bound    pvc-xxxxx   10Gi       RWO            rawfile-localpv
# app-data   Bound    pvc-xxxxx   20Gi       RWO            rawfile-localpv
```

Check events and conditions if it takes long:

```shell
kubectl describe pvc app-data
```

Under the hood: the `csi-resizer` calls the controller, which forwards the request over
the internal gRPC channel to the node that owns the volume; the node grows the backing
file, resizes the loop device and expands the filesystem online.

## Step 3 — Verify inside the pod

```shell
kubectl exec app -- df -hT /data
# Filesystem     Type  Size  Used Avail Use% Mounted on
# /dev/loop3     ext4   20G  1.1G   18G   6% /data
```

No pod restart is needed — the new capacity is visible immediately after the resize
completes.

## Block-mode volumes

Block volumes (`volumeMode: Block`) are also expandable. If the volume is currently
**unstaged** (no pod using it), only the backing file is grown and node-side expansion
is skipped; the device shows the new size the next time it is attached. The application
inside the pod is responsible for recognizing the larger device.

## Limitations

| Item | Status |
|---|---|
| Online expansion (ext4/xfs/btrfs) | ✅ |
| Expansion while pod is running | ✅ |
| Shrinking (online or offline) | ❌ not supported — requests to reduce size are rejected by Kubernetes |
| Expansion beyond pool free space | ❌ fails with `Not enough disk space` (`RESOURCE_EXHAUSTED`) |

## Troubleshooting

| Symptom | Fix |
|---|---|
| PVC capacity never updates | Is `allowVolumeExpansion: true` on the SC? Is the controller Deployment running (`capabilities.resize.enabled`)? Check `kubectl -n openebs logs deploy/<release>-controller`. |
| `Not enough disk space` | The volume's pool on its node lacks free capacity — free space or grow the underlying disk. Check `rawfile_pool_remaining_capacity_bytes`. |
| `Resizing capabilities are disabled` | Set `capabilities.resize.enabled=true` in chart values and upgrade the release. |
| Filesystem size unchanged but PV shows new size | Node-side expansion pending — ensure the pod's node plugin is healthy; kubelet triggers `NodeExpandVolume` on the mounted node. |

## Related guides

- [Creating Volumes](./volumes.md)
- [Monitoring & Metrics](../monitoring.md) — watch pool capacity before/after resizes
