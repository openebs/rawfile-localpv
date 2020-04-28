RawFilePV
===

Kubernetes LocalPVs on Steroids

Install
---
`helm install -n kube-system rawfile-csi ./deploy/charts/rawfile-csi/`

Usage
---

Create a `StorageClass` with your desired options:

```
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: my-sc
provisioner: rawfile.hamravesh.com
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
```

Features
---

- [x] Direct I/O: Near-zero disk performance overhead
- [x] Dynamic provisioning
- [x] Enforced volume size limit
- [x] Thin provisioned
- [x] Access Modes
    - [x] ReadWriteOnce
    - ~~ReadOnlyMany~~
    - ~~ReadWriteMany~~
- [ ] Volume modes
    - [x] `Filesystem` mode
    - [ ] `Block` mode
- [x] Volume metrics
- [ ] Supports fsTypes
- [ ] Online expansion: If fs supports it (e.g. ext4, btrfs)
- [ ] Online shrinking: If fs supports it (e.g. btrfs)
- [ ] Offline expansion/shrinking
- [ ] Ephemeral inline volume
- [ ] Snapshots: If the fs supports it (e.g. btrfs)
