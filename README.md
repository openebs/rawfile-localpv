[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fopenebs%2Frawfile-localpv.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fopenebs%2Frawfile-localpv?ref=badge_shield)

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
allowVolumeExpansion: true
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
- [x] Online expansion: If fs supports it (e.g. ext4, btrfs)
- [ ] Online shrinking: If fs supports it (e.g. btrfs)
- [ ] Offline expansion/shrinking
- [ ] Ephemeral inline volume
- [ ] Snapshots: If the fs supports it (e.g. btrfs)


## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fopenebs%2Frawfile-localpv.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fopenebs%2Frawfile-localpv?ref=badge_large)