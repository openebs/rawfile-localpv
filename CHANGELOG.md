# 📄 Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - YYYY-MM-DD

### Added ✨

- Add Support for setting Compute Resources for API Server
- Add documentation for async volume replication with [VolSync](https://volsync.readthedocs.io/)

### Fixed 🐛

- StorageClass CopyOnWrite with value `""` now correctly defaults to auto-detected as opposed to `false`

### Changed ♻️

- StorageClass and VolumeSnapshotClass are now updatable with helm upgrade command

### Removed 🗑️ ⚠️

### Internal 🔧

- Support for creating multiple local [kind](https://kind.sigs.k8s.io/) rawfile clusters

### Known Issues 🚫

- ReadOnly attribute in PVC template not fully handled
- When using thin provisioning, user must specify the format options preventing `mkfs` from discarding blocks (`-K` for xfs/btrfs, `-E nodiscard` for ext4). Also see this [issue](https://github.com/openebs/rawfile-localpv/issues/295)
- For ext4, volumes available space might be smaller than intended due to defaulting to reserve 5% of the blocks for privileged users. This can be circumvented via format options (`-m 0`)

---

## [v0.15.0] - 2026-08-17 ⚠️ Breaking Changes

### Added ✨

- API Server with OpenAPI spec and Swagger UI
- Complete documentation [in-tree](https://github.com/openebs/rawfile-localpv/blob/v0.15.0/docs/README.md)
- [OpenEBS Website](https://openebs.io/docs) documentation for [rawfile-localpv](https://openebs.io/docs/user-guides/local-storage-user-guide/local-pv-rawfile/rawfile-overview)

### Fixed 🐛

- Volume expansion failure by using findmnt with more stable output instead of using mount

### Changed ♻️

- Uses CoW when it's enabled and supported between source and destination on snapshot restore
- Conditional snapshot-controller with leader-election

### Removed 🗑️ ⚠️

- Deprecated configurations/Features removed
  - Top Level dataDirPath and reservedCapacity in Helm Chart Values
  - FileSystem-Level (BTRfs) Snapshots, Snapshots are not removed, but not available anymore (Remove them before upgrading)

### Internal 🔧

- New endpoints for the Internal gRPC server
- Multiple dependency bumps across the stack, ensuring security and stability
- GA DNS is now configurable

### Known Issues 🚫

- ReadOnly attribute in PVC template not fully handled
- When using thin provisioning, user must specify the format options preventing `mkfs` from discarding blocks (`-K` for xfs/btrfs, `-E nodiscard` for ext4). Also see this [issue](https://github.com/openebs/rawfile-localpv/issues/295)
- For ext4, volumes available space might be smaller than intended due to defaulting to reserve 5% of the blocks for privileged users. This can be circumvented via format options (`-m 0`)

---

## [v0.14.1] - 2026-06-10

### Added ✨

- Added `rawfile_pool_backing_fs_available_bytes` and `rawfile_pool_backing_fs_usage_bytes` metrics, exposing `statvfs(fs_avail)` and `statvfs(fs_size - fs_avail)` for the storage pool's backing filesystem. Replace the (v0.14.0) `rawfile_pool_available_bytes` / `rawfile_pool_usage_bytes`. The rename completes the `rawfile_pool_backing_fs_*` naming convention introduced in v0.14.0 with `rawfile_pool_backing_fs_capacity_bytes`: any metric measuring the whole backing filesystem (not just the rawfile-allocated slice) carries the `_backing_fs_` infix, so a single look at a metric name tells you whether it's pool-scoped or backing-FS-scoped.

- Helm chart:
  - Add `capacityPollInterval` parameter for external-provisioner, determining how long the external-provisioner waits before checking for storage capacity changes.

### Fixed 🐛

- When Task Manager would read tasks without "retry_count" key present, it'd throw a `KeyError` exception. Add defaults when "retry_count" key is read.

- Helm chart:
  - Quote image names templated values so special characters do not break the resulting YAML.

### Changed ♻️

### Removed 🗑️ ⚠️

- ⚠️ Removed `rawfile_pool_available_bytes` and `rawfile_pool_usage_bytes`. They were introduced in v0.14.0 with an inconsistent name (used the `rawfile_pool_*` prefix despite measuring the **backing filesystem** including non-rawfile tenants). Use the equivalently-valued replacements:

  ```text
  rawfile_pool_available_bytes  →  rawfile_pool_backing_fs_available_bytes
  rawfile_pool_usage_bytes      →  rawfile_pool_backing_fs_usage_bytes
  ```

  Anyone using these in dashboards or alerts will need to do a metric-name find/replace.

### Internal 🔧

### Known Issues 🚫

- ReadOnly attribute in PVC template not fully handled
- When using thin provisioning, user must specify the format options preventing `mkfs` from discarding blocks (`-K` for xfs/btrfs, `-E nodiscard` for ext4). Also see this [issue](https://github.com/openebs/rawfile-localpv/issues/295)
- For ext4, volumes available space might be smaller than intended due to defaulting to reserve 5% of the blocks for privileged users. This can be circumvented via format options (`-m 0`)

---

## [v0.14.0] - 2026-05-19

### Added ✨

- Added `csiSideCars.image.registry` and `csiSideCars.image.pullPolicy` to configure CSI sidecar container images
- Added `analytics.enabled` to enable/disable analytics locally
- Added `node.podAnnotations` to set custom annotations on the node DaemonSet pods
- Added per-storage-pool Prometheus metrics (`rawfile_pool_capacity_bytes`, `rawfile_pool_backing_fs_capacity_bytes`, `rawfile_pool_available_bytes`, `rawfile_pool_usage_bytes`, `rawfile_pool_reserved_capacity_bytes`, `rawfile_pool_remaining_capacity_bytes`, `rawfile_pool_volumes_physical_bytes`, `rawfile_pool_volumes_logical_bytes`, `rawfile_pool_volume_count`, `rawfile_pool_info`) and per-volume additions (`rawfile_volume_physical_bytes`, `rawfile_volume_info`); existing `rawfile_remaining_capacity_bytes`, `rawfile_volume_used_bytes`, and `rawfile_volume_total_bytes` are unchanged. Note: `rawfile_pool_capacity_bytes` reflects the pool's allocated capacity (`fs_size − reserved_capacity`), matching the driver's internal "capacity reserved for this pool" model; `rawfile_pool_backing_fs_capacity_bytes` exposes the raw filesystem size from statvfs.

### Fixed 🐛

### Changed ♻️

- `global.imageRegistry` now overrides all image registries when set

### Removed 🗑️

- This release introduces a breaking change by removing `global.k8sImageRegistry` , `node.image` and `controller.image`

### Internal 🔧

### Known Issues 🚫

- ReadOnly attribute in PVC template not fully handled
- When using thin provisioning, user must specify the format options preventing `mkfs` from discarding blocks (`-K` for xfs/btrfs, `-E nodiscard` for ext4). Also see this [issue](https://github.com/openebs/rawfile-localpv/issues/295)
- For ext4, volumes available space might be smaller than intended due to defaulting to reserve 5% of the blocks for privileged users. This can be circumvented via format options (`-m 0`)

---

## [v0.13.1] - 2026-03-11

### Added ✨

### Fixed 🐛

- Eliminate potential race involving Volume/Snapshot creation tasks
- Catch and log errors when retrying tasks, and try again, instead of letting exceptions propagate
- Temporary snapshot directory is not counted as a snapshot anymore (would lead to Node Plugin to refuse to delete data/metadata directories even when PersistentVolume itself is deleted)
- When creating volumes, reference the storage pool's capacity that's actually used instead of the default one

### Changed ♻️

- Always dry-run volume garbage collection on startup, for better observability
- Stop logging "attached loopback devices" queries

### Removed 🗑️

### Internal 🔧

Task Manager:

- add metadata to task information (create/save/retry timestamps, last error)
- store task in memory before adding done callback (fixing aforementioned race)

Tests:

- better logging

### Known Issues 🚫

- ReadOnly attribute in PVC template not fully handled
- When using thin provisioning, user must specify the format options preventing `mkfs` from discarding blocks (`-K` for xfs/btrfs, `-E nodiscard` for ext4). Also see this [issue](https://github.com/openebs/rawfile-localpv/issues/295)
- Prometheus metrics use capacity sum across all the pools, instead of values per pool. This may lead to confusing results. Also see this [issue](https://github.com/openebs/rawfile-localpv/issues/294)
- For ext4, volumes available space might be smaller than intended due to defaulting to reserve 5% of the blocks for privileged users. This can be circumvented via format options (`-m 0`)

---

## [v0.13.0] - 2026-03-03 ⚠️ Breaking Changes

### Added ✨

- Application:
  - Introduce storage pools, allowing to have multiple filesystems backing provisioned volumes on a single node ⚠️
    - Deprecate `node.dataDirPath` and `reservedCapacity` in favor of storage pool specific values ⚠️
    - Add `storagePool` parameter to storage class definition to tie a given class to a pool
    - Add `defaultPool` parameter to be used if no pool is specified explicitly
  - Turn undesired capabilities off to save resources (see `capabilities`)
  - Add `reservedCapacityMode` switch determining how reserved capacity is calculated. It is now possible to reserve capacity just for the storage pool, or for everything else but the pool

- Helm chart:
  - `hostNetwork` switch for the node component enabling `hostNetwork` mode
  - Customize ports
  - Specify `affinity` and `nodeSelector`
  - Specify `auth.secretName` to enable managing authentication secret outside of the chart
  - Specify resources explicitly for every container

### Fixed 🐛

- Fix `reservedCapacity` parsing that could lead to undesired results (e.g. "10%" parsed as 10 bytes)

### Changed ♻️

- Capacity calculations account only for actual allocated blocks as opposed to logical size of the files. This changes the calculations for thin (i.e. sparse) backing files and enables overprovisioning ⚠️
- Reserved capacity is calculated based on total space as opposed to free ⚠️

### Removed 🗑️

- Remove `capacity_override` chart parameter (not a breaking change as it was not factually affecting calculations)

### Internal 🔧

### Known Issues 🚫

- ReadOnly attribute in PVC template not fully handled
- When using thin provisioning, user must specify the format options preventing `mkfs` from discarding blocks (`-K` for xfs/btrfs, `-E nodiscard` for ext4). Also see this [issue](https://github.com/openebs/rawfile-localpv/issues/295)
- Prometheus metrics use capacity sum across all the pools, instead of values per pool. This may lead to confusing results. Also see this [issue](https://github.com/openebs/rawfile-localpv/issues/294)
- For ext4, volumes available space might be smaller than intended due to defaulting to reserve 5% of the blocks for privileged users. This can be circumvented via format options (`-m 0`)

---

## [v0.12.2] - 2025/12/08

### Fixed 🐛

- Support IPv6 in the internal rawfile server

### Known Issues 🚫

- ReadOnly attribute in PVC template not fully handled

## [v0.12.1] - 2025-12-01

### Fixed 🐛

- Fixed helm storage class `isDefault` templating

### Changed ♻️

- Validate volume readiness before mounting

### Known Issues 🚫

- ReadOnly attribute in PVC template not fully handled

## [v0.12.0] - 2025-11-20 ⚠️ Breaking Changes

### Added ✨

- Volumes Snapshots using the rawfile image itself
  - If the underlying fs supports it, we use `reflinks` for `COW`
  - Otherwise, a deep copy is performed and application is frozen with `fsfreeze`
  - However, if `fsfreeze` is not enable in the storage class, then snapshots are not allowed for in used volumes
  - `COW` can be manually disabled or forcefully enabled
- Volume Clone on the same node
  - Leveraging the same rawfile snapshots
- Trivy container image scanning on push and PRs
- Kubelet path configuration

### Fixed 🐛

- Incorrect response object when not using json
- Missing service monitor interval

### Changed ♻️

- Use gRPC server for internal communication
  - Replaces previous pod which was used for controller->node communication
- Updated base image to debian trixie
- Support separate data and metadata dir ⚠️

### Removed 🗑️

- Btrfs Snapshots support ⚠️
  - Existing snapshots may still be deleted on this version

### Internal 🔧

- Add reflink support to CI `kind` environment
- Updated various dependency packages
- Dependabot groups changes in single PR
- Snapshot copy manager

### Known Issues 🚫

- ReadOnly attribute in PVC template not fully handled

## [v0.11.0] - 2025-07-22 ⚠️ Breaking Changes

### Added ✨

- A new logging system for easier tracing/support
- Serialization of CSI volume operations
- New storage class parameter: `formatOptions` to specify filesystem creation/formatting options
- New storage class parameter: `thinProvision` to control full storage allocation or on-demand
- Support for reserved storage/capacity override support on nodes via helm variable configuration: `reservedCapacity` and `capacityOverride`
- Analytics are now being sent to the OpenEBS GA4 project

### Fixed 🐛

- Add missing helm components for btrfs snapshots on K8s
- Delete snapshot if source data has already been deleted
- Atomically update metadata and file image
- Use `mountOptions` from the storage class when mounting a filesystem
- Increased CSI volume resize timeout from 10s to 30s
- Add return error code to `fallocate`

### Changed ♻️

- Refactored FS Support and Utilities to be more standard
- ⚠️ Thick volumes are now the default ⚠️  \
  To retain existing thin behaviour you may set `thinProvision` storage class parameter to `true`
- Switched to the official K8s client library
- Try to load K8s incluster config first (removes noddy warning message in-cluster)
- Change CLI to pydantic for better validation and UX

### Removed 🗑️

- Removed K8s manifest file deployment type

### Internal 🔧

- Increase kubelet sync frequency for testing
- Add and use [Mergify](https://mergify.com/) bot for `GitHub Actions`
- Improved `nixos-shell` experience for dev
- Add helm-docs pre-commit hook
- Added Contributor documentation
- Set provisioner version using the pyproject toml file
- Improve reliability and usability of volume verifier and task pod
- Run CI smoke tests as `fail-fast`

### Known Issues 🚫

- ReadOnly attribute in PVC template not fully handled
- Volume restore/clone not implemented

---

## [v0.10.0] - 2025-06-18

> [GitHub Release](https://github.com/openebs/rawfile-localpv/releases/tag/v0.10.0)

### Added ✨

- Direct I/O for near-zero disk performance overhead
- Support for `Block` volume mode
- Helm chart package publishing
- Add `fsType` to storageClass in helm
- Signal handling for graceful pod termination in K8s

### Fixed 🐛

- Volume expansion issues
- Parent folder creation and idempotency on volume publishing
- Race condition during volume deletion (img file leak)
- Loop device cleanup and idempotency
- Skip node expand if the volume is not staged

### Security 🛡️

- Restrict permissions on existing data/image path  \
  Update existing ones on migration

### Changed ♻️

- Updated CSI spec to v1.10.0
- Refactored deployment manifests
- Improved logging and error handling
- ⚠️ Large Helm Chart overhaul ⚠️

### Internal 🔧

- Refactored deployment manifests
- Improved README.md documentation
- Migrated CI from `Travis` to `GitHub Actions`
- Implemented stale action to manage old PRs/issues
- Added smoke tests for reliable builds
- Upgraded Python environment (now using Poetry for dependency management)
- Multiple dependency bumps across the stack, ensuring security and stability
- Added Dependabot for automated dependency updates
- Introduced a CODEOWNERS file to streamline code ownership
- Local testing with kind or vm through nixos-shell
- Add pre-commit and format the code
- Fix OpenSSF link and Add pre-commit.ci badge
- Skip tests on docs only changes

### Known Issues 🚫

- ReadOnly attribute in PVC template not fully handled
- Volume restore/clone not implemented
