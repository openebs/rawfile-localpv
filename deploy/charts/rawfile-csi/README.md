# rawfile-csi

![Version: 0.8.0](https://img.shields.io/badge/Version-0.8.0-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: 0.8.0](https://img.shields.io/badge/AppVersion-0.8.0-informational?style=flat-square)

RawFile Driver Container Storage Interface

**Homepage:** <https://openebs.io/>

## Source Code

* <https://github.com/openebs/rawfile-localpv>

## Requirements

Kubernetes: `>= 1.21`

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| controller.externalResizer.image.registry | string | `"registry.k8s.io"` | Image registry for `csi-resizer` |
| controller.externalResizer.image.repository | string | `"sig-storage/csi-resizer"` | Image Repository for `csi-resizer` |
| controller.externalResizer.image.tag | string | `"v1.2.0"` | Image tag for `csi-resizer` |
| controller.priorityClassName | string | `"system-cluster-critical"` | priorityClassName for controller component since this part is critical for cluster `system-cluster-critical` is default |
| controller.resources | object | `{}` | Sets compute resources for controller component |
| controller.tolerations | list | `[{"effect":"NoSchedule","key":"node-role.kubernetes.io/master","operator":"Equal","value":"true"}]` | Tolerations for controller component |
| global.imagePullPolicy | string | `"IfNotPresent"` | Default pull policy for images |
| global.imagePullSecrets | list | `[]` | Default image pull secret for images |
| global.imageRegistry | string | `"docker.io"` | Default image registry for Images from DockerHub |
| global.k8sImageRegistry | string | `"registry.k8s.io"` | Default image registry for Images from Kubernetes (registry.k8s.io) |
| image.pullPolicy | string | `"IfNotPresent"` | Default image pull policy for node and controller components |
| image.registry | string | `""` | Image registry for rawfile-localpv (default is global.imageRegistry) |
| image.repository | string | `"openebs/rawfile-localpv"` | Image repository for rawfile-localpv |
| image.tag | string | `""` | Default image tag for node and controller components (uses AppVersion if empty) |
| imagePullSecrets | list | `[]` | Sets image pull secret while pulling images from a private registry |
| metrics.enabled | bool | `true` | Completely enable or disable metrics |
| metrics.port | int | `9100` | Sets metrics port |
| metrics.serviceMonitor.enabled | bool | `false` | Enables prometheus service monitor |
| metrics.serviceMonitor.interval | string | `"1m"` | Sets prometheus target interval |
| node.dataDirPath | string | `"/var/csi/rawfile"` | Data dir path for provisioner to be used by provisioner |
| node.driverRegistrar.image.registry | string | `""` | Image Registry for `csi-node-driver-registrar` |
| node.driverRegistrar.image.repository | string | `"sig-storage/csi-node-driver-registrar"` | Image Repository for `csi-node-driver-registrar` |
| node.driverRegistrar.image.tag | string | `"v2.2.0"` | Image Tag for `csi-node-driver-registrar` |
| node.externalProvisioner.image.registry | string | `""` | Image Registry for `csi-provisioner` |
| node.externalProvisioner.image.repository | string | `"sig-storage/csi-provisioner"` | Image Repository for `csi-provisioner` |
| node.externalProvisioner.image.tag | string | `"v2.2.2"` | Image Tag for `csi-provisioner` |
| node.externalSnapshotter.image.registry | string | `""` | Image Registry for `csi-snapshotter` |
| node.externalSnapshotter.image.repository | string | `"sig-storage/csi-snapshotter"` | Image Repository for `csi-snapshotter` |
| node.externalSnapshotter.image.tag | string | `"v5.0.1"` | Image Tag for `csi-snapshotter` |
| node.image.pullPolicy | string | `""` | Overrides default image pull policy for node component |
| node.image.repository | string | `""` | Overrides default image repository for node component |
| node.image.tag | string | `""` | Overrides default image tag for node component |
| node.metrics.enabled | bool | `false` |  |
| node.priorityClassName | string | `"system-node-critical"` | priorityClassName for node component since this part is critical for node `system-node-critical` is default |
| node.resources | object | `{}` | Sets compute resources for node component |
| node.tolerations | list | `[{"operator":"Exist"}]` | Tolerations for node component |
| provisionerName | string | `"rawfile.csi.openebs.io"` | Name of the registered CSI Driver in the cluster |
| storageClasses[0].allowVolumeExpansion | bool | `true` | volumes are able to expand/resize or not? |
| storageClasses[0].enabled | bool | `true` | Enable or disable StorageClass |
| storageClasses[0].name | string | `"rawfile-localpv"` | Name of the StorageClass |
| storageClasses[0].reclaimPolicy | string | `"Delete"` | Sets default reclaimPolicy for StorageClass volumes |
| storageClasses[0].volumeBindingMode | string | `"WaitForFirstConsumer"` | Sets volumeBindingMode for StorageClass |

----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.14.2](https://github.com/norwoodj/helm-docs/releases/v1.14.2)
