# rawfile-localpv

![Version: 0.15.0](https://img.shields.io/badge/Version-0.15.0-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: 0.15.0](https://img.shields.io/badge/AppVersion-0.15.0-informational?style=flat-square)

RawFile Driver Container Storage Interface

**Homepage:** <https://openebs.io/>

## Source Code

* <https://github.com/openebs/rawfile-localpv>

## Requirements

Kubernetes: `>= 1.21`

| Repository | Name | Version |
|------------|------|---------|
|  | crds | 0.0.1 |

## Install and Upgrades

Please follow the [install guide](https://github.com/openebs/rawfile-localpv/tree/v0.15.0/docs/install-guide.md)

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| analytics.enabled | bool | `true` | Enable OpenEBS analytics which help track engine traction and usage. |
| analytics.gaDnsNameservers | string | `"8.8.8.8:53"` | Comma-separated DNS nameservers (each optionally `ip:port`) used to resolve the analytics endpoint. Leave empty to use the cluster's default resolver (CoreDNS). |
| auth.enabled | bool | `true` | Enables authentication for internal gRPC server |
| auth.secretName | string | `""` | If managing secrets outside the chart, use this to reference the secret name; otherwise, leave empty. |
| auth.token | string | `""` | Sets authentication token for internal gRPC server, will generate one if nothing provided |
| capabilities.apiServer.enabled | bool | `true` | Sets whether API Server has been enabled or not |
| capabilities.resize.enabled | bool | `true` | Sets whether volume resizing is enabled. If disabled, don't deploy controller component |
| capabilities.snapshots.enabled | bool | `true` | Sets whether taking volume snapshots is enabled. Required for volume cloning. Runs externalSnapshotter and snapshotController containers. |
| controller.affinity | string | `nil` | Affinities for controller component |
| controller.externalResizer.image.pullPolicy | string | `nil` | Image pull policy for `csi-resizer` |
| controller.externalResizer.image.registry | string | `""` | Image registry for `csi-resizer` |
| controller.externalResizer.image.repository | string | `"sig-storage/csi-resizer"` | Image Repository for `csi-resizer` |
| controller.externalResizer.image.tag | string | `"v2.2.1"` | Image tag for `csi-resizer` |
| controller.externalResizer.resources | object | `{}` | Sets compute resources for external-resizer container |
| controller.grpcWorkers | int | `10` | Number of gRPC workers for controller component |
| controller.nodeSelector | string | `nil` | nodeSelector for controller component |
| controller.priorityClassName | string | `"system-cluster-critical"` | priorityClassName for controller component since this part is critical for cluster `system-cluster-critical` is default |
| controller.resources | object | `{}` | Sets compute resources for controller component |
| controller.tolerations | list | `[{"effect":"NoSchedule","key":"node-role.kubernetes.io/control-plane","operator":"Exists"},{"effect":"NoSchedule","key":"node-role.kubernetes.io/master","operator":"Exists"}]` | Tolerations for controller component |
| crds.csi.volumeSnapshots.enabled | bool | `true` | Install Volume Snapshot CRDs |
| crds.enabled | bool | `true` | Disables the installation of all CRDs if set to false |
| csiSideCars | object | `{"image":{"pullPolicy":"IfNotPresent","registry":"registry.k8s.io"}}` | Image registry for CSI Sidecars |
| csiSideCars.image.pullPolicy | string | `"IfNotPresent"` | Image pull policy for csi sidecars |
| csiSideCars.image.registry | string | `"registry.k8s.io"` | Image registry for csi sidecars |
| global.analytics.enabled | string | `nil` | Global override for GA analytics |
| global.analytics.gaDnsNameservers | string | `nil` | Global override for DNS nameservers used to resolve the analytics endpoint |
| global.imagePullPolicy | string | `""` | Global override for image pull policy |
| global.imagePullSecrets | list | `[]` | Global image pull secrets (merged with local imagePullSecrets and not overridden) - secret |
| global.imageRegistry | string | `""` | Global override for image registry |
| image.pullPolicy | string | `"IfNotPresent"` | Default image pull policy for node and controller components |
| image.registry | string | `"docker.io"` | Image registry for rawfile-localpv (can be overridden by global.imageRegistry) |
| image.repository | string | `"openebs/rawfile-localpv"` | Image repository for rawfile-localpv |
| image.tag | string | `nil` | Default image tag for node and controller components (uses AppVersion if empty) |
| imagePullSecrets | list | `[]` | Sets image pull secret while pulling images from a private registry |
| logFormat | string | `"json"` | Format of the logs (json, pretty) |
| logLevel | string | `"INFO"` | Level of the logs (DEBUG, INFO, etc.) |
| metrics.enabled | bool | `true` | Completely enable or disable metrics |
| metrics.port | int | `9100` | Sets metrics port |
| metrics.serviceMonitor.enabled | bool | `false` | Enables prometheus service monitor |
| metrics.serviceMonitor.interval | string | `"1m"` | Sets prometheus target interval |
| node.affinity | string | `nil` | Affinities for node component |
| node.defaultFs | string | `"ext4"` | Default filesystem type for rawfile volumes (Currently supports `btrfs`, `xfs` and `ext4` [which is default]) |
| node.defaultPool | string | `"default"` | Default storage pool name |
| node.driverRegistrar.healthzPort | int | `9809` | Healthcheck port for driver-registrar |
| node.driverRegistrar.image.pullPolicy | string | `nil` | Image pull policy for `csi-node-driver-registrar` |
| node.driverRegistrar.image.registry | string | `""` | Image Registry for `csi-node-driver-registrar` |
| node.driverRegistrar.image.repository | string | `"sig-storage/csi-node-driver-registrar"` | Image Repository for `csi-node-driver-registrar` |
| node.driverRegistrar.image.tag | string | `"v2.17.0"` | Image Tag for `csi-node-driver-registrar` |
| node.driverRegistrar.resources | object | `{}` | Sets compute resources for driver-registrar container |
| node.externalProvisioner.capacityPollInterval | string | `"1m"` | Sets capacity poll interval for `csi-provisioner`, determining how long the external-provisioner waits before checking for storage capacity changes. |
| node.externalProvisioner.image.pullPolicy | string | `nil` | Image pull policy for `csi-provisioner` |
| node.externalProvisioner.image.registry | string | `""` | Image Registry for `csi-provisioner` |
| node.externalProvisioner.image.repository | string | `"sig-storage/csi-provisioner"` | Image Repository for `csi-provisioner` |
| node.externalProvisioner.image.tag | string | `"v6.3.0"` | Image Tag for `csi-provisioner` |
| node.externalProvisioner.resources | object | `{}` | Sets compute resources for external-provisioner container |
| node.externalSnapshotter.image.pullPolicy | string | `nil` | Image pull policy for `csi-snapshotter` |
| node.externalSnapshotter.image.registry | string | `""` | Image Registry for `csi-snapshotter` |
| node.externalSnapshotter.image.repository | string | `"sig-storage/csi-snapshotter"` | Image Repository for `csi-snapshotter` |
| node.externalSnapshotter.image.tag | string | `"v8.6.0"` | Image Tag for `csi-snapshotter` |
| node.externalSnapshotter.resources | object | `{}` | Sets compute resources for external-snapshotter container |
| node.grpcWorkers | int | `10` | Number of gRPC workers for node component |
| node.hostNetwork | bool | `false` | Enables hostNetwork for node component |
| node.internalGRPC.port | int | `4500` | Port Number used for internal communication gRPC server |
| node.internalGRPC.workers | int | `10` | gRPC worker count used for internal communication |
| node.kubeletPath | string | `"/var/lib/kubelet"` | Kubelet path (Set to `/var/lib/k0s/kubelet` for k0s) |
| node.metadataDirPath | string | `"/var/local/openebs/rawfile/{{ .Release.Name }}/meta"` | Metadata dir path for rawfile volumes metadata and tasks store file |
| node.metrics.enabled | bool | `false` |  |
| node.nodeSelector | string | `nil` | nodeSelector for node component |
| node.podAnnotations | object | `{}` | Annotations for the node DaemonSet pods |
| node.priorityClassName | string | `"system-node-critical"` | priorityClassName for node component since this part is critical for node `system-node-critical` is default |
| node.resources | object | `{}` | Sets compute resources for node component |
| node.snapshotController.enabled | bool | `true` | Runs the snapshot-controller container. There should only be one snapshot-controller per cluster, so disable this if the cluster already runs one. That controller must be started with `--enable-distributed-snapshotting=true`, or rawfile snapshots will never be provisioned. Requires `capabilities.snapshots.enabled`. |
| node.snapshotController.image.pullPolicy | string | `nil` | Image pull policy for `snapshot-controller` |
| node.snapshotController.image.registry | string | `""` | Image Registry for `snapshot-controller` |
| node.snapshotController.image.repository | string | `"sig-storage/snapshot-controller"` | Image Repository for `snapshot-controller` |
| node.snapshotController.image.tag | string | `"v8.6.0"` | Image Tag for `snapshot-controller` |
| node.snapshotController.resources | object | `{}` | Sets compute resources for snapshot-controller container |
| node.storagePools | object | `{"default":{"path":"/var/local/openebs/rawfile/default-pool/"}}` | Storage pools configuration |
| node.tolerations | string | `nil` | Tolerations for node component |
| provisionerName | string | `"rawfile.csi.openebs.io"` | Name of the registered CSI Driver in the cluster |
| snapshotClasses[0].deletionPolicy | string | `"Delete"` | Sets deletion policy for snapshots created using this class (Delete or Retain) |
| snapshotClasses[0].enabled | bool | `true` | Enable or disable SnapshotClass |
| snapshotClasses[0].isDefault | bool | `false` | Make the snapshot class as default |
| snapshotClasses[0].name | string | `"rawfile-localpv"` | Name of the SnapshotClass |
| storageClasses[0].allowVolumeExpansion | bool | `true` | volumes are able to expand/resize or not? |
| storageClasses[0].copyOnWrite | string | `""` | Enables CoW on storage class (defaults to autodetect) |
| storageClasses[0].enabled | bool | `true` | Enable or disable StorageClass |
| storageClasses[0].formatOptions | list | `[]` | Sets format options for filesystem volumes |
| storageClasses[0].freezeFs | string | `""` | Enables FreezeFS on storage class can be used to enable snapshotting of inused volumes when CoW is disabled/not supported (False by default) |
| storageClasses[0].fsType | string | `"ext4"` | Sets filesystem type for volumes (Currently supports `btrfs`, `xfs` and `ext4` [which is default]) |
| storageClasses[0].isDefault | bool | `false` | Make the storage class as default |
| storageClasses[0].mountOptions | list | `[]` | Sets mount options for filesystem volumes |
| storageClasses[0].name | string | `"rawfile-localpv"` | Name of the StorageClass |
| storageClasses[0].reclaimPolicy | string | `"Delete"` | Sets default reclaimPolicy for StorageClass volumes |
| storageClasses[0].storagePool | string | `""` | Sets storage pool used for volumes |
| storageClasses[0].thinProvision | string | `""` | Enables thin provisioning of volumes |
| storageClasses[0].volumeBindingMode | string | `"WaitForFirstConsumer"` | Sets volumeBindingMode for StorageClass |
