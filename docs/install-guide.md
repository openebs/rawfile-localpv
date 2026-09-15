# Install Guide

## Install

### Via Helm

```shell
helm repo add rawfile-localpv https://openebs.github.io/rawfile-localpv
helm repo update rawfile-localpv
helm install rawfile-localpv rawfile-localpv/rawfile-localpv -n openebs --create-namespace
```

> [!TIP]
We suggest you familiarize yourself with the [Charts' README.md](../deploy/helm/rawfile-localpv/README.md) and the [Charts' values.yaml](../deploy/helm/rawfile-localpv/values.yaml), as you may want to tune it to your liking

## Usage

You can create one or more storage classes using chart, by default we have a storage class named `rawfile-localpv`, but you can change the name or other options by changing chart values

## Upgrade

Before upgrading please read through the [Changelog](../CHANGELOG.md) as well as this document and follow any suggested recommendations to ensure a smooth upgrade

> [!WARNING]
Don't blind upgrade to a potentially breaking version as additional steps may be required

We try to do our best to follow [semantic versioning](https://semver.org/), but mistakes can happen. If you encounter any unexpected breaking change from our part, please do let us know!

### Upgrading to v0.15.x

> [!IMPORTANT]
Upgrade to the latest patch of v0.15.x to include the bug fix for this [issue](https://github.com/openebs/rawfile-localpv/issues/402)

This version introduces the following breaking changes:

- ⚠️ Removed deprecated `node.dataDirPath` and `reservedCapacity` in favor of storage pool specific values (See [Upgrade](#upgrading-to-v0130) for more details) to avoid data unavailability after upgrade \
  If you haven't switched to storage pools in v0.13.x, a default pool named "data-dir" has been already created for you, and you should define it in the values and make it default, to make sure your volumes are migrated correctly
  For example if you had:
  ```yaml
  node:
    dataDirPath: /var/csi/rawfile # This is the default value
  ```
  It should be changed to:
  ```yaml
  defaultPool: data-dir
  node:
    storagePools:
      data-dir:
        path: /var/csi/rawfile
  ```
  After first start, you can change the default pool. \
  To migrate your volumes to the new pool, you can define a new storage class with the newer pool, then clone your volumes to the new pool and rename PVCs to use newer PVs (By removing PVCs while keeping PVs). \
  This will ensure your volumes are migrated correctly. After that, you can delete the old storage class and the default pool.
- ⚠️ Removed filesystem-level snapshot support, Snapshots are not removed, but not available anymore (Remove them before upgrading you can access data inside the snapshot using by accessing img file of the volume directly)

### Upgrading to v0.14.1

This version introduces the following breaking changes:

- ⚠️ Removed `rawfile_pool_available_bytes` and `rawfile_pool_usage_bytes`. They were introduced in v0.14.0 with an inconsistent name (used the `rawfile_pool_*` prefix despite measuring the **backing filesystem** including non-rawfile tenants). Use the equivalently-valued replacements:

  ```text
  rawfile_pool_available_bytes  →  rawfile_pool_backing_fs_available_bytes
  rawfile_pool_usage_bytes      →  rawfile_pool_backing_fs_usage_bytes
  ```

  Anyone using these in dashboards or alerts will need to do a metric-name find/replace.

We believe these changes, despite being technically breaking, are small enough to not warrant minor version bump.

### Upgrading to v0.14.0

This version introduces the following breaking changes:

- Support for `global.k8sImageRegistry` has been removed. \
  Use `global.imageRegistry` to override all image registries. \
  Alternatively, configure local registry values or use `csiSideCarImageRegistry` for CSI sidecar images if needed.

### Upgrading to v0.13.0

This version introduces the following breaking changes:

- Deprecate `node.dataDirPath` and `reservedCapacity` in favor of storage pool specific values \
  If you defined these to be different than defaults, migrate them to `node.storagePools.default` (or any other pool you create and choose to be your default pool, along with defined storage classes). \
  If you continue to use `node.dataDirPath`, a default pool named "data-dir" will be created for you, however this will be removed in the future versions. \
  Since the default storage pool path is different from the default `node.dataDirPath`, Before upgrading change your default pool path to the value of the `node.dataDirPath` (It's `/var/csi/rawfile` by default) \
  By default a pool named default will be created you can change its path to the value of `node.dataDirPath` or customize pool configurations, after upgrade all of the Volumes inside will point to the default pool \
  For example if you had:
  ```yaml
  node:
    dataDirPath: /var/csi/rawfile
  ```
  It should be changed to:
  ```yaml
  defaultPool: default
  node:
    storagePools:
      default:
        path: /var/csi/rawfile
  ```
  This release has a known issue where after upgrade some operations may fail after switching to storage pools, And it will get fixed after upgrading to v0.15.x

- Capacity calculations account only for actual allocated blocks as opposed to logical size of the files. This changes the calculations for thin (i.e. sparse) backing files and enables overprovisioning \
  If you relied on the fact overprovisioning is impossible even when using thin provisioning, this release changes that. If you'd like to opt out of overprovisioning, use thick provisioning without discarding blocks during formatting (for more, see this [issue](https://github.com/openebs/rawfile-localpv/issues/295)). On the other hand, if you wanted to overprovision, just use thin provisioning.
- Reserved capacity is calculated based on total space as opposed to free \
  Be cautios that available capacity calculations will change after the upgrade if `reservedCapacity` was non-zero.

### Upgrading to v0.12.0

This version introduces the following breaking changes:

- Btrfs snapshots has been deprecated \
  New snapshots cannot be taken but we still allow deleting existing ones.
- Separate Data and Metadata dir \
  The metadata defaults to $DATA/meta and the data is copied automatically by the node plugin

### Upgrading to v0.11.0

This version introduces the following breaking changes:

- Volumes are thick provisioned by default  \
  To retain existing thin behaviour you may set `thinProvision` storage class parameter to `false`
- Manifest install file has been removed \
  Please use the helm chart package going forward. You may also generate equivalent file with `helm template`
- Analytics have been added and enabled default \
  We'd appreciate it if you kept them enabled, but of course you may disable them through the helm var `.globals.analytics.enabled`

## Uninstall

Before uninstalling `rawfile-localpv` please make sure all resources created through `rawfile-localpv` are deleted:

1. Volume Snapshots
2. Persistent Volume Claims
3. Persistent Volumes

This will ensure there's no leaked mounts or linux loop devices in your system.

After you've done so, you should uninstall using the same method which you had used for install.

### Installed using Helm

```shell
helm uninstall rawfile-localpv -n openebs
```

### Installed using manifest (removed)

```shell
kubectl delete -f https://github.com/openebs/rawfile-localpv/raw/refs/heads/develop/deploy/rawfile-localpv-driver.yaml
```

[!WARNING]
Be sure to use the exact same yaml file which you had used to install

---

After uninstalling you may want to delete the `rawfile-localpv` data directory from each node.
