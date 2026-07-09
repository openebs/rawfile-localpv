# Monitoring & Metrics

Each node plugin exposes Prometheus metrics on `metrics.port` (default **9100**).
Enable scraping either through your own scrape config or via the chart's
`metrics.serviceMonitor.enabled=true` (Prometheus Operator), with the scrape interval
set by `metrics.serviceMonitor.interval` (default `1m`). Metrics can be disabled
entirely with `metrics.enabled=false`.

Gauges are organized in three aggregation levels: **node**, **pool** and **volume**.

## Node-level

| Metric | Labels | Description |
|---|---|---|
| `rawfile_remaining_capacity_bytes` | `node` | Free capacity for new volumes on this node (excluding reserved storage). |

## Per-pool

| Metric | Labels | Description |
|---|---|---|
| `rawfile_pool_capacity_bytes` | `node`, `pool` | Capacity allocated to the pool for provisioning (backing FS size minus reserved capacity). |
| `rawfile_pool_remaining_capacity_bytes` | `node`, `pool` | Free capacity for new volumes on the pool (excluding reserved storage). |
| `rawfile_pool_reserved_capacity_bytes` | `node`, `pool` | Bytes reserved per the pool's `reservedCapacity` configuration. |
| `rawfile_pool_backing_fs_capacity_bytes` | `node`, `pool` | Total size of the filesystem backing the pool (statvfs). |
| `rawfile_pool_backing_fs_available_bytes` | `node`, `pool` | Available space on the backing FS — includes the reserved slice and non-rawfile space. |
| `rawfile_pool_backing_fs_usage_bytes` | `node`, `pool` | Used space on the backing FS — includes non-rawfile tenants (kubelet ephemeral storage, logs, …). |
| `rawfile_pool_volumes_physical_bytes` | `node`, `pool` | Sum of physical (on-disk) sizes of all volumes in the pool. |
| `rawfile_pool_volumes_logical_bytes` | `node`, `pool` | Sum of logical (provisioned) sizes of all volumes in the pool. |
| `rawfile_pool_volume_count` | `node`, `pool` | Number of volumes provisioned on the pool. |
| `rawfile_pool_info` | `node`, `pool`, `mode`, `default_pool` | Static pool info; always `1`, use labels for joins. |

## Per-volume

| Metric | Labels | Description |
|---|---|---|
| `rawfile_volume_used_bytes` | `node`, `volume` | Actual disk space used inside the volume. |
| `rawfile_volume_total_bytes` | `node`, `volume` | Space allocated (provisioned) to the volume. |
| `rawfile_volume_physical_bytes` | `node`, `volume` | Physical (on-disk) size of the volume's backing file. |
| `rawfile_volume_info` | `node`, `volume`, `pool`, `sparse`, `thin_provision` | Static volume info; always `1`, use labels for joins. |

## Useful queries

Volume fullness (alert when a volume nears its limit):

```promql
rawfile_volume_used_bytes / rawfile_volume_total_bytes > 0.9
```

Pool overcommit ratio (thin provisioning):

```promql
sum by (node, pool) (rawfile_pool_volumes_logical_bytes)
  / rawfile_pool_capacity_bytes
```

Real free space left in a pool (guard against thin-provisioning exhaustion):

```promql
rawfile_pool_remaining_capacity_bytes < 10 * 1024^3
```

Join volume usage with its pool via info metrics:

```promql
rawfile_volume_used_bytes
  * on (node, volume) group_left (pool) rawfile_volume_info
```

## Renamed metrics (v0.14.1)

`rawfile_pool_available_bytes` and `rawfile_pool_usage_bytes` (introduced in v0.14.0)
were renamed — update dashboards/alerts:

```
rawfile_pool_available_bytes  →  rawfile_pool_backing_fs_available_bytes
rawfile_pool_usage_bytes      →  rawfile_pool_backing_fs_usage_bytes
```

## Logs

Structured logs (`logFormat: json` by default, `pretty` for humans) with levels from
`TRACE` to `CRITICAL` (`logLevel` chart value). Every gRPC request/response is logged
with context at debug levels.

## REST API

When `capabilities.apiServer.enabled=true`, a REST API provides cluster-wide
introspection of nodes, pools, volumes and background tasks — see
[Architecture § REST API Server](./architecture.md#rest-api-server-optional).
