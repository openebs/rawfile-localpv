[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fopenebs%2Frawfile-localpv.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fopenebs%2Frawfile-localpv?ref=badge_shield)

## RawFile-LocalPV
The RawFile-LocalPV OpenEBS Data-Engine is a simialr but more flexible, yet more complex.. derication of the LocalPV-Hostpath Data-Engine. <BR>

This are a few reasons to consider using node-based (rather than network-based) storage architetcure:
> - Performance: Almost no network-based storage solution can keep up with baremetal disk performance in terms of IOPS/latency/throughput combined. And you’d like to get the best out of the SSD you’ve got!
> - On-premise Environment: You might not be able to afford the cost of upgrading all your networking infrastructure, to get the best out of your network-based storage solution.
> - Complexity: Network-based solutions are distributed systems. And distributed systems are not easy! You might want to have a system that is easier to understand and to reason about. Also, with less complexity, you can fix unpredicted issues more easily.

### Using node-based storage
The OpenEBS LocalPV-HostPath Data-Engine makes it pretty easy to automatically provision hostPath PVs and use them in your workloads. But, there are known limitations though:

> [!IMPORTANT]
> - You can’t monitor volume usage: There are hacky workarounds to run “du” regularly, but that could prove to be a performance killer, since it could put a lot of burden on your CPU and cause your filesystem cache to fill up. Not really good for a production workload.
> - You can’t enforce hard limits on your volume’s size: Again, you can hack your way around it, with the same caveats.
> - You are stuck with whatever filesystem your kubelet node is offering
> - You can’t customize your filesystem:

<BR>
### All the above issues stem from the same root cause: 
   - hostPath/LocalPVs are simple bind-mounts from the host filesystem into the pod.

### The idea behind RawFile-LocalPB 
To use a Filesystem based 'extant file' as the emulated block device (i.e. a soft-LUN block device), and leverage the LINUX loop device to associate that soft-LUN file as a complete flexibe block device (i.e. an emulated soft disk device). At this point you can create a PV with a fileystem on it. This allows you to...
> [!NOTE]
> - You can monitor volume usage by running `df -hT` in `O(1)` since each soft-LUN block device is mounted separately on the local node (displaying utilization status/metrics or each mountpoint).
> - The size limit is enforced by the operating system, based on the backing file system capacity and soft-lun device file size.
> - Since volumes are backed by different files, each soft-lin device file can be formatted using different filesystems, and/or customized with different filesystem options.


### Prerequisites
---
- Kubernetes: 1.21+

## Installation

`helm install -n kube-system rawfile-csi ./deploy/charts/rawfile-csi/`

Usage
---

Create a `StorageClass` with your desired options:

```
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: my-sc
provisioner: rawfile.csi.openebs.io
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

Features
---

- [x] Direct I/O: Near-zero disk performance overhead
- [x] Dynamic provisioning
- [x] Enforced volume size limit
- [x] Access Modes
    - [x] ReadWriteOnce
    - ~~ReadOnlyMany~~
    - ~~ReadWriteMany~~
- [ ] Volume modes
    - [x] `Filesystem` mode
    - [ ] `Block` mode
- [x] Volume metrics
- [x] Supports fsTypes: `ext4`, `btrfs`, `xfs`
- [x] Online expansion: If fs supports it (e.g. ext4, btrfs, xfs)
- [ ] Online shrinking: If fs supports it (e.g. btrfs)
- [ ] Offline expansion/shrinking
- [ ] Ephemeral inline volume
- [ ] Snapshots: If the fs supports it (e.g. btrfs)


## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fopenebs%2Frawfile-localpv.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fopenebs%2Frawfile-localpv?ref=badge_large)
