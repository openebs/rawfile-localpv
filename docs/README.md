# OpenEBS LocalPV RawFile Documentation

OpenEBS LocalPV RawFile (`rawfile-localpv`) is a CSI driver that dynamically provisions
node-local Persistent Volumes backed by sparse/preallocated **raw files** ("extent files")
attached via Linux **loop devices**. This gives you local-disk performance with the
manageability of real block devices: enforced size limits, per-volume filesystems,
snapshots, cloning, expansion and rich metrics.

## Table of Contents

### Getting Started

- [Quickstart & User Guide](./quickstart.md) — prerequisites, deployment, and first volume
- [Install Guide](./install-guide.md) — install, upgrade and uninstall instructions
- [Examples](./examples.md) — ready-to-apply manifests for common scenarios

### User Guides

- [Creating and Configuring Volumes](./user-guide/volumes.md) — StorageClasses, PVCs, filesystem & block mode, thin/thick, deletion
- [Snapshots & Restore](./user-guide/snapshots.md) — taking snapshots and restoring them into new PVCs
- [Cloning Volumes](./user-guide/cloning.md) — PVC-to-PVC copies
- [Resizing Volumes](./user-guide/resize.md) — online volume expansion
- [Storage Pools](./user-guide/storage-pools.md) — multiple pools, capacity reservation, tiering
- [Async Replication with VolSync](./user-guide/replication.md) — cross-node/cross-cluster replication

### Reference

- [Features](./features.md) — capability matrix and feature deep dives
- [StorageClass Configuration](./storageclass.md) — every parameter configurable via StorageClass
- [Helm Chart Values](../deploy/helm/rawfile-localpv/README.md) — full list of chart values
- [Monitoring & Metrics](./monitoring.md) — Prometheus metrics reference

### Internals

- [Architecture](./architecture.md) — components, data flow, and volume lifecycle
- [Task Manager Design](./design/taskmanager.md) — async task execution subsystem

### Project

- [Contributor Guide](./contributor.md) — building, testing and submitting changes
- [Release Process](./release.md)
- [Changelog](../CHANGELOG.md)
