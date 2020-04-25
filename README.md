RawFilePV
===

Kubernetes LocalPVs on Steroids

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
- [ ] Volume metrics
- [ ] Supports fsTypes
- [ ] Online expansion: If fs supports it (e.g. ext4, btrfs)
- [ ] Online shrinking: If fs supports it (e.g. btrfs)
- [ ] Offline expansion/shrinking
- [ ] Ephemeral inline volume
- [ ] Snapshots: If the fs supports it (e.g. btrfs)
