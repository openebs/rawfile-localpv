# OpenEBS Local PV RawFile

[![CNCF Status](https://img.shields.io/badge/cncf%20status-sandbox-blue.svg)](https://www.cncf.io/projects/openebs/)
[![LICENSE](https://img.shields.io/github/license/openebs/openebs.svg)](./LICENSE)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/4137/badge)](https://www.bestpractices.dev/projects/4137)
[![Slack](https://img.shields.io/badge/chat-slack-ff1493.svg?style=flat-square)](https://kubernetes.slack.com/messages/openebs)
[![Community Meetings](https://img.shields.io/badge/Community-Meetings-blue)](https://github.com/openebs/community/blob/HEAD/README.md#community)
[![CLOMonitor](https://img.shields.io/endpoint?url=https://clomonitor.io/api/projects/cncf/openebs/badge)](https://clomonitor.io/projects/cncf/openebs)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/openebs/rawfile-localpv/develop.svg)](https://results.pre-commit.ci/latest/github/openebs/rawfile-localpv/develop)

## Overview

There are a few reasons to consider using node-based (rather than network-based) storage architecture:

- Performance: Almost no network-based storage solution can keep up with baremetal disk performance in terms of IOPS/latency/throughput combined. And you’d like to get the best out of the SSD you’ve got!
- On-premise Environment: You might not be able to afford the cost of upgrading all your networking infrastructure, to get the best out of your network-based storage solution.
- Complexity: Network-based solutions are distributed systems. And distributed systems are not easy! You might want to have a system that is easier to understand and to reason about. Also, with less complexity, you can fix unpredicted issues more easily.

<BR>

> [!WARNING]
> We're still pre-v1, meaning our helm api or storage class parameters might have breaking changes

### RawFile vs HostPath

Another OpenEBS provisioner, the [LocalPV-HostPath](https://github.com/openebs/dynamic-localpv-provisioner/) makes it pretty easy to automatically provision HostPath PVs and use them in your workloads. That being said, it has the following known limitations:

- You can’t monitor volume usage: There are hacky workarounds to run “du” regularly, but that could prove to be a performance killer, since it could put a lot of burden on your CPU and cause your filesystem cache to fill up. Not really good for a production workload.
- You can’t enforce hard limits on your volume’s size: Again, you can hack your way around it, with the same caveats.
- You are stuck with whatever filesystem your kubelet node is offering.
- You can’t customize your filesystem.

<BR>

> [!IMPORTANT]
All the above issues stem from the same root cause:
HostPath/LocalPVs are simple bind-mounts from the host filesystem into the pod.

### The idea behind RawFile-LocalPV

To use a Filesystem based `extent file` as the emulated block device (i.e. a soft-LUN block device), and leverage LINUX loop devices to associate that soft-LUN file as a complete flexible block device (i.e. an emulated soft disk device).

At this point you can create a PV with a filesystem on it, which adds the following benefits:

- You can monitor volume usage by running `df -hT` in `O(1)` since each soft-LUN block device is mounted separately on the local node (displaying utilization status/metrics or each mount point).
- The size limit is enforced by the operating system, based on the backing file system capacity and soft-lun device file size.
- Since volumes are backed by different files, each soft-lun device file can be formatted using different filesystems, and/or customized with different filesystem options.

## How to Use

Please follow the instructions from the [Install Guide](./docs/install-guide.md).

## Documentation

Full documentation lives in the [docs](./docs/README.md) directory:

- [Quickstart & User Guide](./docs/quickstart.md) — prerequisites, deployment, first volume
- User guides: [Volumes](./docs/user-guide/volumes.md) · [Snapshots & Restore](./docs/user-guide/snapshots.md) · [Cloning](./docs/user-guide/cloning.md) · [Resize](./docs/user-guide/resize.md) · [Storage Pools](./docs/user-guide/storage-pools.md)
- [Examples](./docs/examples.md) — PVCs, block mode, snapshots, clones, expansion
- [StorageClass Configuration](./docs/storageclass.md) — all storage class parameters
- [Features](./docs/features.md) — capability matrix and deep dives
- [Monitoring & Metrics](./docs/monitoring.md) — Prometheus metrics reference
- [Architecture](./docs/architecture.md) — components and volume lifecycle
- [Helm Chart Values](./deploy/helm/rawfile-localpv/README.md)

## Features

- [x] Direct I/O: Near-zero disk performance overhead
- [x] Dynamic provisioning
- [x] Enforced volume size limit
- [x] Access Modes
  - [x] ReadWriteOnce
  - [ ] ReadWriteOncePod
  - ~~ReadOnlyMany~~
  - ~~ReadWriteMany~~
- [ ] Volume modes
  - [x] `Filesystem` mode
  - [x] `Block` mode
    - The `readOnly` attribute in the PVC template is not currently handled properly
- [x] Volume metrics
- [x] Supports fsTypes: `ext4`, `btrfs`, `xfs`
- [x] Online expansion: If fs supports it (e.g. ext4, btrfs, xfs)
- [ ] Online shrinking: If fs supports it (e.g. btrfs)
- [ ] Offline expansion/shrinking
- [x] Volume Cloning
  - [x] Same node cloning
  - [ ] Cross node cloning (in progress)
- [x] Volume Snapshots
  - ~~[x] Filesystem-level snapshots: `btrfs` supported~~
  - [x] Block Level snapshots

---

## Project Activity

![Alt](https://repobeats.axiom.co/api/embed/09ac8b1ccb26584b212fae37e18cf4d5b6a1f761.svg "Repobeats analytics image")

## License compliance

[![FOSSA Status](https://app.fossa.com/api/projects/custom%2B162%2Fgithub.com%2Fopenebs%2Frawfile-localpv.svg?type=large&issueType=license)](https://app.fossa.com/projects/custom%2B162%2Fgithub.com%2Fopenebs%2Frawfile-localpv?ref=badge_large&issueType=license)

## OpenEBS is a [CNCF Sandbox Project](https://www.cncf.io/projects/openebs)

![OpenEBS is a CNCF Sandbox Project](https://github.com/cncf/artwork/blob/main/other/cncf/horizontal/color/cncf-color.png)
