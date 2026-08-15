# Quickstart & User Guide

This guide walks you from an empty cluster to a running workload backed by a
RawFile LocalPV volume.

## Prerequisites

- **Kubernetes**: a recent Kubernetes distribution (kubeadm, k3s, k0s, kind, etc.).
  For k0s set `node.kubeletPath=/var/lib/k0s/kubelet`.
- **Linux nodes** with loop-device support (the standard `loop` kernel module).
- **Filesystem tooling** for your chosen fsType is bundled in the driver image
  (`ext4`, `xfs`, `btrfs`).
- **Helm 3** for installation.
- **Snapshot CRDs**: installed automatically by the chart
  (`crds.csi.volumeSnapshots.enabled=true`); disable if your cluster already provides
  them.
- **Disk space** on each node under the configured storage-pool path(s).
- **CoW-capable pool filesystem** (optional, recommended for snapshots/clones): cheap
  copy-on-write snapshots and clones require the pool's backing filesystem to support
  reflinks — e.g. btrfs, or XFS created with `mkfs.xfs -m reflink=1`. See
  [Storage Pools § CoW-capable pools](./user-guide/storage-pools.md#copy-on-write-cow-capable-pools).

> [!NOTE]
> Volumes are **node-local**. A pod using a RawFile PV is always scheduled onto the node
> that holds the volume's data. Only `ReadWriteOnce` access mode is supported.

## Step 1 — Install the driver

```shell
helm repo add rawfile-localpv https://openebs.github.io/rawfile-localpv
helm repo update rawfile-localpv
helm install rawfile-localpv rawfile-localpv/rawfile-localpv \
  -n openebs --create-namespace
```

See the [Install Guide](./install-guide.md) for upgrade/uninstall procedures and the
[chart README](../deploy/helm/rawfile-localpv/README.md) for all values.

A recommended production-style values file:

```yaml
node:
  defaultPool: default
  storagePools:
    default:
      path: /var/local/openebs/rawfile/default-pool/
      reservedCapacity: "10%"          # keep 10% of the disk for the OS & others
      reservedCapacityMode: plain

storageClasses:
  - name: rawfile-localpv
    enabled: true
    isDefault: false
    volumeBindingMode: WaitForFirstConsumer
    allowVolumeExpansion: true
    reclaimPolicy: Delete
    fsType: ext4

metrics:
  enabled: true
  serviceMonitor:
    enabled: true    # if you run Prometheus Operator
```

Verify:

```shell
kubectl -n openebs get pods
kubectl get csidrivers rawfile.csi.openebs.io
kubectl get sc rawfile-localpv
```

## Step 2 — Create a PVC

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-data
spec:
  storageClassName: rawfile-localpv
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 5Gi
```

The PVC stays `Pending` until a pod uses it (`WaitForFirstConsumer`) — this is expected.

## Step 3 — Use it in a workload

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
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
        claimName: my-data
```

Once the pod is scheduled, the volume is created on that node, formatted, and mounted.
Check it:

```shell
kubectl exec my-app -- df -hT /data
```

## Day-2 operations

### Expand a volume

```shell
kubectl patch pvc my-data -p '{"spec":{"resources":{"requests":{"storage":"10Gi"}}}}'
```

Expansion is **online** for ext4/xfs/btrfs — no pod restart needed
(requires `allowVolumeExpansion: true` on the StorageClass, the default).

### Snapshot a volume

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: my-data-snap
spec:
  volumeSnapshotClassName: rawfile-localpv
  source:
    persistentVolumeClaimName: my-data
```

> [!NOTE]
> On a pool **without CoW** support and with `freezeFs` disabled, a snapshot of a
> volume that is still mounted by a pod will not complete (`READYTOUSE` stays
> `false` while the driver retries) until the pod is removed. See
> [Snapshots § Snapshotting in-use volumes](./user-guide/snapshots.md#snapshotting-in-use-volumes).

### Restore / clone

Create a new PVC with a `dataSource` referencing the snapshot (or another PVC for
cloning). See [Examples](./examples.md). Note: restore/clone happens on the **same
node** as the source, and cloning requires roughly 3× the volume size of free pool
space during the operation.

### Monitor usage

Per-volume/pool/node Prometheus metrics are exposed on port `9100` of each node-plugin
pod (enable `metrics.serviceMonitor.enabled` for Prometheus Operator). See
[Monitoring & Metrics](./monitoring.md).

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| PVC stuck `Pending` | No pod consuming it yet (`WaitForFirstConsumer`), or no node has enough free pool capacity — check `kubectl get csistoragecapacities -A` and node-plugin logs. |
| `Insufficient disk space` on clone | Cloning needs ≥ 3× the volume size free in the pool during the copy. |
| `Volume in use` on PVC delete | A pod still mounts the volume; delete consumers first. |
| Pod can't schedule after node loss | Volumes are node-local; data on a lost node is not replicated. |
| Verbose diagnostics needed | Set `logLevel: DEBUG` (or `TRACE`) and `logFormat: pretty` in chart values. |

Increase verbosity, then inspect logs:

```shell
kubectl -n openebs logs ds/<release>-node -c csi-driver
```

## Next steps

- [StorageClass Configuration](./storageclass.md) — thin provisioning, fsType,
  format/mount options, CoW, storage pools
- [Features](./features.md) — full capability matrix
- [Architecture](./architecture.md) — how it all works
