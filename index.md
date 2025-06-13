## RawFile-LocalPV [Experimental]

[![CNCF Status](https://img.shields.io/badge/cncf%20status-sandbox-blue.svg)](https://www.cncf.io/projects/openebs/)
[![LICENSE](https://img.shields.io/github/license/openebs/openebs.svg)](https://github.com/openebs/rawfile-localpv/blob/HEAD/LICENSE)
[![Slack](https://img.shields.io/badge/chat-slack-ff1493.svg?style=flat-square)](https://kubernetes.slack.com/messages/openebs)
[![Community Meetings](https://img.shields.io/badge/Community-Meetings-blue)](https://github.com/openebs/community/blob/HEAD/README.md#community)

## Overview

The RawFile-LocalPV OpenEBS Data-Engine is a similar but more flexible, yet more complex derivation of the LocalPV-HostPath Data-Engine. <BR>

There are a few reasons to consider using node-based (rather than network-based) storage architecture:
> - Performance: Almost no network-based storage solution can keep up with baremetal disk performance in terms of IOPS/latency/throughput combined. And you’d like to get the best out of the SSD you’ve got!
> - On-premise Environment: You might not be able to afford the cost of upgrading all your networking infrastructure, to get the best out of your network-based storage solution.
> - Complexity: Network-based solutions are distributed systems. And distributed systems are not easy! You might want to have a system that is easier to understand and to reason about. Also, with less complexity, you can fix unpredicted issues more easily.

### Using node-based storage

The OpenEBS LocalPV-HostPath Data-Engine makes it pretty easy to automatically provision HostPath PVs and use them in your workloads. But, there are known limitations though:

> **Important:**
> - You can’t monitor volume usage: There are hacky workarounds to run “du” regularly, but that could prove to be a performance killer, since it could put a lot of burden on your CPU and cause your filesystem cache to fill up. Not really good for a production workload.
> - You can’t enforce hard limits on your volume’s size: Again, you can hack your way around it, with the same caveats.
> - You are stuck with whatever filesystem your kubelet node is offering.
> - You can’t customize your filesystem.

<BR>

#### All the above issues stem from the same root cause:
- HostPath/LocalPVs are simple bind-mounts from the host filesystem into the pod.

### The idea behind RawFile-LocalPV

To use a Filesystem based 'extent file' as the emulated block device (i.e. a soft-LUN block device), and leverage the LINUX loop device to associate that soft-LUN file as a complete flexible block device (i.e. an emulated soft disk device). At this point you can create a PV with a fileystem on it. This allows you to...

> **NOTE:**
> - You can monitor volume usage by running `df -hT` in `O(1)` since each soft-LUN block device is mounted separately on the local node (displaying utilization status/metrics or each mountpoint).
> - The size limit is enforced by the operating system, based on the backing file system capacity and soft-lun device file size.
> - Since volumes are backed by different files, each soft-lin device file can be formatted using different filesystems, and/or customized with different filesystem options.


### Prerequisites
---

- Kubernetes: 1.21+

## Installation

### Via Helm

```shell
helm repo add rawfile-localpv https://openebs.github.io/rawfile-localpv
helm repo update rawfile-localpv
helm install -n openebs rawfile-localpv rawfile-localpv/rawfile-localpv
```

> Refer to chart's [README](./deploy/helm/rawfile-localpv/README.md) to see the [values](./deploy/helm/rawfile-localpv/values.yaml) documentation if you need to customize it

### Via manifests

```shell
kubectl apply -f https://github.com/openebs/rawfile-localpv/raw/refs/heads/develop/deploy/rawfile-localpv-driver.yaml
```

> Manifests are generated from helm chart's default values using `helm template` command

Usage
---

You can create one or more storage classes using chart, by default we have a storage class named `rawfile-localpv`, but you can change the name or other options by changing chart values

Features
---

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
- [ ] Ephemeral inline volume
- [x] Filesystem-level snapshots: `btrfs` supported
