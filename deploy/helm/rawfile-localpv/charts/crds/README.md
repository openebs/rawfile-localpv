# crds

![Version: 0.0.1](https://img.shields.io/badge/Version-0.0.1-informational?style=flat-square)

A Helm chart that collects CustomResourceDefinitions (CRDs).

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| csi.volumeSnapshots.annotations | object | `{}` | Annotations to be added to all CRDs |
| csi.volumeSnapshots.enabled | bool | `true` | Install Volume Snapshot CRDs |
| csi.volumeSnapshots.keep | bool | `true` | Keep CRDs on chart uninstall |
