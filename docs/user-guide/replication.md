# User Guide: Async Replication with VolSync

RawFile LocalPV volumes are strictly **node-local** — the driver itself has no
replication (see [Features § Current limitations](../features.md#current-limitations)).
For cross-node or cross-cluster async replication / DR, pair it with
[VolSync](https://volsync.readthedocs.io/), a Kubernetes operator that copies PVC data
via a `ReplicationSource` (on the source) and a `ReplicationDestination` (on the
destination) using a pluggable "mover".

This guide covers what actually works with RawFile LocalPV today, and the gotchas that
aren't obvious from VolSync's own docs.

## Before you begin

- VolSync installed on **both** sides (same cluster+different namespace, or two separate
  clusters — VolSync itself must be running wherever each CR lives).
- Snapshots enabled on RawFile LocalPV (chart default: `capabilities.snapshots.enabled=true`)
  — needed for `copyMethod: Snapshot`, the recommended copy method (see
  [Snapshots & Restore](./snapshots.md)).
- A `VolumeSnapshotClass` and `StorageClass` for the driver (chart default: both named
  `rawfile-localpv`).

### Block volumes don't work yet

This isn't a RawFile LocalPV-specific issue.

See [backube/volsync discussion #495](https://github.com/backube/volsync/discussions/495)
and [issue #556](https://github.com/backube/volsync/issues/556) for upstream status.

## Step 1 — Set up the destination

```yaml
apiVersion: volsync.backube/v1alpha1
kind: ReplicationDestination
metadata:
  name: app-data-dst
spec:
  rsync:
    copyMethod: Snapshot
    capacity: 10Gi
    accessModes: ["ReadWriteOnce"]
    storageClassName: rawfile-localpv
    volumeSnapshotClassName: rawfile-localpv
    # NodePort (or LoadBalancer) needed if the source can't reach a ClusterIP —
    # see "Reaching the destination" below.
    serviceType: NodePort
```

```shell
kubectl apply -f replicationdestination.yaml
```

VolSync immediately provisions a **working/cache PVC** (named `<name>-dst` by default)
and starts the mover's server side — this happens *before* any data has synced, so a
freshly-`Bound` PVC with an empty filesystem is expected, not a sign of success yet.
Once a sync completes, `status.latestImage` points at a `VolumeSnapshot` of that PVC —
that snapshot, not the live cache PVC, is the point-in-time copy you should restore from.

> [!IMPORTANT]
> The dynamically-provisioned destination PVC and its `latestImage` snapshots are owned
> by the `ReplicationDestination` and are **deleted automatically if you delete it** —
> this is documented, intentional VolSync behavior, not a bug. If you need the replicated
> data to survive deleting/recreating the CR, pre-create your own PVC and reference it via
> `spec.rsync.destinationPVC` instead of letting VolSync provision one.

## Step 2 — Get the address, port, and SSH key secret

```shell
kubectl get replicationdestination app-data-dst -o jsonpath='{.status.rsync}'
```

> [!WARNING]
> `status.rsync.address` is the Service's **ClusterIP** — it's populated regardless of
> `serviceType`, and is only reachable from inside the destination's own cluster. If
> you're replicating across clusters (or otherwise can't route to a ClusterIP), you must
> work out a reachable address yourself: check the actual `Service` object for the
> assigned `NodePort` (`kubectl get svc <name>-rsync-dst`, port shown as `22:<nodePort>/TCP`),
> then pair it with any node address that's actually routable from the source side (e.g.
> two `kind` clusters on the same Docker network share node container IPs).

VolSync also generates an SSH keypair, split across three secrets
(`<name>-main-...`, `<name>-dest-...`, `<name>-src-...`). Copy the `-src-` one — it's
what the source side needs — to wherever the `ReplicationSource` will run:

```shell
kubectl get secret <name>-src-<name> -o json \
  | jq '{apiVersion, kind, type, data, metadata: {name: .metadata.name, namespace: "<source-namespace>"}}' \
  | kubectl --context <source-context> apply -f -
```

## Step 3 — Set up the source

```yaml
apiVersion: volsync.backube/v1alpha1
kind: ReplicationSource
metadata:
  name: app-data-src
spec:
  sourcePVC: app-data
  trigger:
    schedule: "*/30 * * * *"   # or `manual: <any-string>` for one-off syncs
  rsync:
    copyMethod: Snapshot
    volumeSnapshotClassName: rawfile-localpv
    address: <reachable-address-from-step-2>
    port: <nodePort-from-step-2>
    sshKeys: <name>-src-<name>   # the secret copied in step 2
```

```shell
kubectl apply -f replicationsource.yaml
```

> [!WARNING]
> `sshKeys` is easy to skip by accident — if omitted, VolSync doesn't fail, it silently
> **generates its own unrelated keypair** for that side. Both sides then have
> self-consistent-looking but mutually-untrusting keys, and every sync attempt fails with
> `Host key verification failed` (or a repeating "accepted, then immediately disconnected"
> pattern if only the client key mismatches) — with no indication in `kubectl get
> replicationsource/replicationdestination` beyond a stuck `SyncInProgress`. Always set
> `sshKeys` explicitly on whichever side didn't generate the keys.

## Verifying a sync

```shell
kubectl get replicationsource app-data-src -o jsonpath='{.status.latestMoverStatus}'
kubectl get replicationdestination app-data-dst -o jsonpath='{.status.latestImage}'
```

A successful sync shows `"result": "Successful"` and, on the destination, an updated
`latestImage` `VolumeSnapshot` name.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `VolumeSnapshot` stuck not `readyToUse`, mover pod not yet started | Normal if the source PVC is actively mounted/written — the driver retries `CreateSnapshot` (`SnapshotCreateVolumeInUse`) until the volume is briefly idle. See [Snapshots & Restore](./snapshots.md#step-1--take-a-snapshot). |
| `Host key verification failed` in mover pod logs | The source's `sshKeys` secret doesn't match the destination's — see the warning in Step 3. Delete the source's self-generated `-main-`/`-dest-`/`-src-` secrets and the `ReplicationSource`, re-copy the destination's `-src-` secret, and re-apply with `sshKeys` set explicitly. |
| SSH auth succeeds but sync still fails, e.g. `truncate ... invalid argument` | You're replicating a `volumeMode: Block` PVC — not supported end-to-end today, see [Block volumes don't work yet](#block-volumes-dont-work-yet). Switch to `Filesystem` mode. |
| Sync never starts across clusters/networks | `status.rsync.address` is a ClusterIP, not reachable externally — use a `NodePort`/`LoadBalancer` Service and a manually-determined reachable address (Step 2). |
| Destination PVC/snapshot disappeared after deleting `ReplicationDestination` | Expected — dynamically-provisioned destination resources are owned by the CR. Use `destinationPVC` for data you need to survive CR deletion. |

## Related guides

- [Snapshots & Restore](./snapshots.md)
- [Creating and Configuring Volumes](./volumes.md)
- [VolSync documentation](https://volsync.readthedocs.io/)
