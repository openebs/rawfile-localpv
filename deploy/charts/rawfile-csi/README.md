# rawfile-csi

![Version: 0.8.0](https://img.shields.io/badge/Version-0.8.0-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: 0.8.0](https://img.shields.io/badge/AppVersion-0.8.0-informational?style=flat-square)

RawFile Driver Container Storage Interface

## Requirements

Kubernetes: `>= 1.21`

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| controller.externalResizer.image.repository | string | `"registry.k8s.io/sig-storage/csi-resizer"` | Image Repository for `csi-resizer` |
| controller.externalResizer.image.tag | string | `"v1.2.0"` | Image tag for `csi-resizer` |
| controller.image.pullPolicy | string | `""` | Overrides default image pull policy for controller component |
| controller.image.repository | string | `""` | Overrides default image repository for controller component |
| controller.image.tag | string | `""` | Overrides default image tag for controller component |
| controller.resources | object | `{}` | Overrides default resources for controller component |
| controller.tolerations | list | `[{"effect":"NoSchedule","key":"node-role.kubernetes.io/master","operator":"Equal","value":"true"}]` | Tolerations for controller component |
| global.image.pullPolicy | string | `"IfNotPresent"` | Default image pull policy for node and controller components |
| global.image.repository | string | `"docker.io/openebs/rawfile-localpv"` | Default image repository for node and controller components |
| global.image.tag | string | `""` | Default image tag for node and controller components (uses AppVersion if empty) |
| global.resources.limits.cpu | int | `1` | Default CPU Limit for node and controller components |
| global.resources.limits.memory | string | `"100Mi"` | Default Memory Limit for node and controller components |
| global.resources.requests.cpu | string | `"10m"` | Default CPU Request (Guaranty) for node and controller components |
| global.resources.requests.memory | string | `"100Mi"` | Default Memory Request (Guaranty) for node and controller components |
| imagePullSecrets | list | `[]` | Sets image pull secret while pulling images from a private registry |
| node.dataDirPath | string | `"/var/lib/rawfile-localpv"` | Data dir path for provisioner to be used by provisioner |
| node.driverRegistrar.image.repository | string | `"registry.k8s.io/sig-storage/csi-node-driver-registrar"` | Image Repository for `csi-node-driver-registrar` |
| node.driverRegistrar.image.tag | string | `"v2.2.0"` | Image Tag for `csi-node-driver-registrar` |
| node.externalProvisioner.image.repository | string | `"registry.k8s.io/sig-storage/csi-provisioner"` | Image Repository for `csi-provisioner` |
| node.externalProvisioner.image.tag | string | `"v2.2.2"` | Image Tag for `csi-provisioner` |
| node.externalSnapshotter.image.repository | string | `"registry.k8s.io/sig-storage/csi-snapshotter"` | Image Repository for `csi-snapshotter` |
| node.externalSnapshotter.image.tag | string | `"v5.0.1"` | Image Tag for `csi-snapshotter` |
| node.image.pullPolicy | string | `""` | Overrides default image pull policy for node component |
| node.image.repository | string | `""` | Overrides default image repository for node component |
| node.image.tag | string | `""` | Overrides default image tag for node component |
| node.metrics.enabled | bool | `false` |  |
| node.resources | object | `{}` | Overrides default resources for node component |
| node.tolerations | list | `[{"operator":"Exist"}]` | Tolerations for node component |
| provisionerName | string | `"rawfile.csi.openebs.io"` | Name of the registered CSI Driver in cluster |
| serviceMonitor.enabled | bool | `false` | Enables prometheus service monitor |
| serviceMonitor.interval | string | `"1m"` | Sets prometheus target interval |
| storageClasses[0].allowVolumeExpansion | bool | `true` | volumes are able to expand/resize or not? |
| storageClasses[0].enabled | bool | `true` | Enable or disable StorageClass |
| storageClasses[0].name | string | `"rawfile-localpv"` | Name of the StorageClass |
| storageClasses[0].reclaimPolicy | string | `"Delete"` | Sets default reclaimPolicy for StorageClass volumes |
| storageClasses[0].volumeBindingMode | string | `"WaitForFirstConsumer"` | Sets volumeBindingMode for StorageClass |

