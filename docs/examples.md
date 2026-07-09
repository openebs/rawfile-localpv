# Examples

Ready-to-apply manifests for common RawFile LocalPV scenarios. All examples assume the
default StorageClass/SnapshotClass names (`rawfile-localpv`) created by the Helm chart.

## 1. Basic PVC + Pod (Filesystem mode)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: example-fs
spec:
  storageClassName: rawfile-localpv
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 2Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: example-fs-pod
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
        claimName: example-fs
```

## 2. Raw Block volume

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: example-block
spec:
  storageClassName: rawfile-localpv
  accessModes: [ReadWriteOnce]
  volumeMode: Block
  resources:
    requests:
      storage: 2Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: example-block-pod
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
        claimName: example-block
```

## 3. Custom StorageClass — thin-provisioned xfs on an NVMe pool

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rawfile-nvme-xfs
provisioner: rawfile.csi.openebs.io
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
mountOptions:
  - noatime
parameters:
  csi.storage.k8s.io/fstype: xfs
  thinProvision: "true"
  storagePool: nvme
```

(Requires an `nvme` pool in `node.storagePools` — see
[StorageClass Configuration](./storageclass.md#storagepool).)

## 4. Volume expansion

```shell
kubectl patch pvc example-fs \
  -p '{"spec":{"resources":{"requests":{"storage":"4Gi"}}}}'
# watch the resize complete (online, no pod restart)
kubectl get pvc example-fs -w
```

## 5. Snapshot and restore

Take a snapshot:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: example-fs-snap
spec:
  volumeSnapshotClassName: rawfile-localpv
  source:
    persistentVolumeClaimName: example-fs
```

Wait for readiness:

```shell
kubectl get volumesnapshot example-fs-snap \
  -o jsonpath='{.status.readyToUse}'
```

Restore into a new PVC (lands on the same node as the source):

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: example-fs-restored
spec:
  storageClassName: rawfile-localpv
  accessModes: [ReadWriteOnce]
  dataSource:
    apiGroup: snapshot.storage.k8s.io
    kind: VolumeSnapshot
    name: example-fs-snap
  resources:
    requests:
      storage: 2Gi
```

## 6. Clone a PVC

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: example-fs-clone
spec:
  storageClassName: rawfile-localpv
  accessModes: [ReadWriteOnce]
  dataSource:
    kind: PersistentVolumeClaim
    name: example-fs
  resources:
    requests:
      storage: 2Gi
```

> [!NOTE]
> Cloning requires roughly 3× the volume size of free pool capacity during the copy and
> currently happens on the same node as the source.

## 7. StatefulSet with volumeClaimTemplates

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: example-sts
spec:
  serviceName: example-sts
  replicas: 3
  selector:
    matchLabels: { app: example-sts }
  template:
    metadata:
      labels: { app: example-sts }
    spec:
      containers:
        - name: app
          image: busybox
          command: ["sh", "-c", "sleep infinity"]
          volumeMounts:
            - name: data
              mountPath: /data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        storageClassName: rawfile-localpv
        accessModes: [ReadWriteOnce]
        resources:
          requests:
            storage: 1Gi
```

Each replica gets its own node-local volume; replicas stay pinned to their node.

## 8. Snapshotting an in-use volume without CoW (`freezeFs`)

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

Volumes of this class are briefly frozen (`fsfreeze`) while snapshots are taken,
producing crash-consistent snapshots even without copy-on-write support.
