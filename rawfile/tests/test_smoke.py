# ruff: noqa: TRY002

import logging
import subprocess
import time

import pytest
from common import fixture_cleanup
from common.helm import HelmReleaseClient
from common.k8s_deployer import Deployer
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from pytest_bdd import given, parsers, scenario, then, when
from retrying import retry
from utils.units import str_to_bool

logger = logging.getLogger(__name__)
helm = HelmReleaseClient()
deployer = Deployer()

namespace = "rawfile-test"
provisioner = "rawfile.csi.openebs.io"
attempt_counter = 0


def short_pvc_name(binding_mode, access_mode, fs_type, volume_mode, mount_options):
    bm_map = {"Immediate": "im", "WaitForFirstConsumer": "wf"}
    am_map = {"ReadWriteOnce": "rwo", "ReadOnlyMany": "rom", "ReadWriteMany": "rwm"}
    vm_map = {"Filesystem": "fs", "Block": "blk"}

    bm = bm_map.get(binding_mode, "u")
    am = am_map.get(access_mode, "u")
    fs = fs_type if fs_type else "null"
    vm = vm_map.get(volume_mode, "u")
    mo = mount_options if mount_options and mount_options != "null" else ""

    parts = [bm, am, fs, vm]
    if mo:
        parts.append(mo[:2])

    return "-".join(parts).lower()


@scenario("smoke.feature", "Create PVCs with different storage parameters")
def test_create_pvcs_with_different_storage_parameters():
    """Create PVCs with different storage parameters."""


@scenario(
    "smoke.feature",
    "Snapshot creates and restores with different parameters and successfully remove it",
)
def test_create_snapshot_with_different_parameters():
    """Snapshot creates and restores with different parameters and successfully remove it"""


@scenario("smoke.feature", "Create PVCs and use them as source for other PVCs")
def test_create_pvcs_as_source_for_other_pvcs():
    """Create PVCs and use them as source for other PVCs."""


@pytest.fixture(scope="module")
def cluster():
    # Start deployer
    deployer.start()
    config.load_kube_config()

    helm.install_rawfile()

    logger.info(f"Prepping test namespace: {namespace}")
    api = client.CoreV1Api()
    body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
    try:
        api.delete_namespace(name=namespace)
    except ApiException as e:
        if e.status != 404:
            raise
    wait_ns_deleted(namespace)
    api.create_namespace(body)


@given("a Kubernetes cluster with rawfile-localpv installed")
def _(cluster):
    """a Kubernetes cluster with rawfile-localpv installed."""


@when(
    parsers.parse(
        "I create a Persistent Volume Claim with {binding_mode} {access_mode} {fs_type} {volume_mode} {mount_options}"
    ),
    target_fixture="pvc",
)
def _(binding_mode, access_mode, fs_type, volume_mode, mount_options):
    mix = short_pvc_name(binding_mode, access_mode, fs_type, volume_mode, mount_options)
    pvc_name = f"pvc-{mix}"
    logger.info(f"Creating PVC: {pvc_name}")

    sc_name = f"sc-{mix}"
    sc = client.V1StorageClass(
        metadata=client.V1ObjectMeta(name=sc_name),
        provisioner=provisioner,
        volume_binding_mode=binding_mode,
        allow_volume_expansion=True,
        mount_options=mount_options.split(",") if mount_options != "null" else None,
        parameters={"csi.storage.k8s.io/fstype": fs_type},
    )
    stor_v1 = client.StorageV1Api()
    try:
        stor_v1.delete_storage_class(name=sc_name)
    except ApiException as e:
        if e.status != 404:
            raise
    stor_v1.create_storage_class(body=sc)

    pvc = client.V1PersistentVolumeClaim(
        metadata=client.V1ObjectMeta(name=pvc_name),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=[access_mode],
            resources=client.V1ResourceRequirements(requests={"storage": "512Mi"}),
            volume_mode=volume_mode,
            storage_class_name=sc_name,
        ),
    )
    core_v1 = client.CoreV1Api()
    pvc = core_v1.create_namespaced_persistent_volume_claim(
        body=pvc, namespace=namespace
    )
    yield pvc
    if not fixture_cleanup():
        return
    logger.info(f"Deleting PVC: {pvc_name}")
    stor_v1.delete_storage_class(name=sc_name)
    try:
        core_v1.delete_namespaced_persistent_volume_claim(
            name=pvc_name, namespace=namespace
        )
        wait_pvc_deleted(pvc_name)
    except ApiException as e:
        if e.status != 404:
            raise


@when("a pod is created with the above PVC", target_fixture="pod")
def _(pvc):
    """a pod is created with the above PVC."""
    pod = create_pod(pvc.metadata.name, pvc)
    yield pod
    if not fixture_cleanup():
        return
    name = pod.metadata.name
    logger.info(f"Deleting POD: {name}")
    try:
        client.CoreV1Api().delete_namespaced_pod(name, namespace)
        wait_pod_deleted(name)
    except ApiException as e:
        if e.status != 404:
            raise


@when("another pod is created with the above PVC", target_fixture="expanded_pod")
def _(expanded_pvc):
    """another pod is created with the above PVC."""
    pod = create_pod(f"expanded-{expanded_pvc.metadata.name}", expanded_pvc, True)
    yield pod
    if not fixture_cleanup():
        return
    name = pod.metadata.name
    logger.info(f"Deleting Expanded POD: {name}")
    try:
        client.CoreV1Api().delete_namespaced_pod(name, namespace)
    except ApiException as e:
        if e.status != 404:
            raise
    wait_pod_deleted(name)


@when("the PVC is expanded", target_fixture="expanded_pvc")
def _(pvc):
    """the PVC is expanded."""
    pvc_name = pvc.metadata.name
    new_size = "1024Mi"
    patch = {"spec": {"resources": {"requests": {"storage": new_size}}}}
    pvc = client.CoreV1Api().patch_namespaced_persistent_volume_claim(
        name=pvc_name, namespace=namespace, body=patch
    )
    logger.info(f"Expanded PVC spec of {pvc_name} to {new_size}")
    yield pvc


@then("the Block PVCs status reflect the expanded size")
def _(expanded_pvc):
    """the Block PVCs status reflect the expanded size."""
    if expanded_pvc.spec.volume_mode == "Block":
        new_size = expanded_pvc.spec.resources.requests["storage"]
        logger.info(
            f"Waiting PVC {expanded_pvc.metadata.name} to be expanded to {new_size}"
        )
        wait_pvc_expanded(expanded_pvc.metadata.name)
        logger.info(
            f"The PVC {expanded_pvc.metadata.name} has been expanded to {new_size}"
        )


@then("the Filesystem PVC is pending node expansion")
def _():
    """the Filesystem PVC is pending node expansion."""


@then("the PVC status reflects the expanded size")
def _(expanded_pvc):
    """the PVC status reflects the expanded size."""
    new_size = expanded_pvc.spec.resources.requests["storage"]
    logger.info(
        f"Waiting PVC {expanded_pvc.metadata.name} to be expanded to {new_size}"
    )
    wait_pvc_expanded(expanded_pvc.metadata.name)
    logger.info(f"The PVC {expanded_pvc.metadata.name} has been expanded to {new_size}")


@then("the POD sees the expanded size")
def _(expanded_pvc, expanded_pod):
    """the POD sees the expanded size."""
    pvc_name = expanded_pvc.metadata.name
    pod_name = expanded_pod.metadata.name
    wait_pod_running(pod_name)
    exec_command = (
        [
            "/bin/sh",
            "-c",
            f"df /{pvc_name} | tail -n 1 | cut -d' ' -f1 | xargs blockdev --getsize64",
        ]
        if expanded_pvc.spec.volume_mode == "Filesystem"
        else ["/bin/sh", "-c", f"blockdev --getsize64 /dev/{pvc_name}"]
    )

    size_bytes = stream(
        client.CoreV1Api().connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=exec_command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
    )
    pvc_size = "1073741824"  # expanded_pvc.spec.resources.requests["storage"]
    assert size_bytes == pvc_size, f"Pod sees PVC as {size_bytes} but pvc is {pvc_size}"


@then("the PVC should be bound")
def _(pvc):
    """the PVC should be bound."""
    if pvc.spec.volume_mode != "Immediate":
        wait_pvc_bound(pvc.metadata.name)
        logger.info(f"PVC {pvc.metadata.name} is Bound")
    else:
        pvc = client.CoreV1Api().read_namespaced_persistent_volume_claim(
            pvc.metadata.name, namespace
        )
        assert pvc.status.phase == "Bound", f"PVC {pvc} not bound???"


@then("the PVC should be bound if Binding mode is Immediate")
def _(pvc):
    """the PVC should be bound if Binding mode is Immediate."""
    if pvc.spec.storage_class_name.count("immediate") > 0:
        wait_pvc_bound(pvc.metadata.name)
        logger.info(f"PVC {pvc.metadata.name} is Bound")
    else:
        logger.info(f"Skipping PVC {pvc.metadata.name} as it won't bind till first use")


@then("the pod should complete with success")
def _(pod, pvc):
    """the pod should complete with success."""
    wait_pod_success(pod.metadata.name)
    logger.info(f"Pod {pod.metadata.name} is complete")
    client.CoreV1Api().delete_namespaced_pod(pod.metadata.name, namespace)
    wait_pod_deleted(pod.metadata.name)
    logger.info(f"Pod {pod.metadata.name} is deleted")
    if pvc.spec.volume_mode == "Block":
        # there's a slight delay between pod deleted and NodeUnstage
        # Adding 2s since CI can be slow at times...
        time.sleep(2)


@retry(
    stop_max_attempt_number=200,
    wait_fixed=100,
)
def wait_pod_success(name):
    global attempt_counter
    attempt_counter += 1
    pod = client.CoreV1Api().read_namespaced_pod(name, namespace)
    message = f"Pod {name} not completed yet"
    if attempt_counter % 5 == 0:
        logger.debug(message)
    assert pod.status.phase == "Succeeded", message


@retry(
    stop_max_attempt_number=200,
    wait_fixed=200,
)
def wait_pod_running(name):
    global attempt_counter
    attempt_counter += 1
    pod = client.CoreV1Api().read_namespaced_pod(name, namespace)
    message = f"Pod {name} not running yet"
    if attempt_counter % 5 == 0:
        logger.debug(message)
    assert pod.status.phase == "Running", message


@retry(
    stop_max_attempt_number=200,
    wait_fixed=100,
)
def wait_pvc_bound(name):
    global attempt_counter
    attempt_counter += 1
    pvc = client.CoreV1Api().read_namespaced_persistent_volume_claim(name, namespace)
    message = f"PVC {name} not bound yet"
    if attempt_counter % 10 == 0:
        logger.debug(message)
    assert pvc.status.phase == "Bound", message


@retry(
    stop_max_attempt_number=200,
    wait_fixed=100,
)
def wait_pvc_unstaged(uid):
    out = subprocess.getoutput("losetup -nl")
    lines = out.splitlines()
    devs = [line.split(":", 1)[0] for line in lines]
    disk = f"pvc-{uid}/disk.img"
    for dev in devs:
        assert disk not in dev, f"PVC {uid} still staged"


@retry(
    stop_max_attempt_number=200,
    wait_fixed=500,
)
def wait_snap_ready(name):
    snapshot = client.CustomObjectsApi().get_namespaced_custom_object(
        group="snapshot.storage.k8s.io",
        version="v1",
        namespace=namespace,
        plural="volumesnapshots",
        name=name,
    )
    ready = snapshot.get("status", {}).get("readyToUse", False)
    assert ready, f"Snapshot {name} is not ready, snapshot info: {snapshot}"


@retry(
    stop_max_attempt_number=200,
    wait_fixed=250,
)
def wait_pvc_expanded(name):
    pvc = client.CoreV1Api().read_namespaced_persistent_volume_claim(name, namespace)
    assert pvc.status.capacity["storage"] == pvc.spec.resources.requests["storage"], (
        f"PVC {name} not expanded yet"
    )


@retry(
    stop_max_attempt_number=200,
    wait_fixed=500,
)
def wait_ns_deleted(name):
    global attempt_counter
    attempt_counter += 1
    try:
        client.CoreV1Api().read_namespace(name=namespace)
        message = f"Namespace {name} not deleted yet"
        if attempt_counter % 2 == 0:
            logger.debug(message)
        raise Exception(message)
    except ApiException as e:
        if e.status != 404:
            raise


@retry(
    stop_max_attempt_number=200,
    wait_fixed=100,
)
def wait_pvc_deleted(name):
    global attempt_counter
    attempt_counter += 1
    try:
        client.CoreV1Api().read_namespaced_persistent_volume_claim(name, namespace)
        message = f"PVC {name} not deleted yet"
        if attempt_counter % 5 == 0:
            logger.debug(message)
        logger.debug(message)
        raise Exception(message)
    except ApiException as e:
        if e.status != 404:
            raise


@retry(
    stop_max_attempt_number=200,
    wait_fixed=100,
)
def wait_pod_deleted(name):
    global attempt_counter
    attempt_counter += 1
    try:
        client.CoreV1Api().read_namespaced_pod(name, namespace)
        message = f"Pod {name} not deleted yet"
        if attempt_counter % 5 == 0:
            logger.debug(message)
        raise Exception(message)
    except ApiException as e:
        if e.status != 404:
            raise


def create_pod(name, pvc, infinite=False):
    pvc_name = pvc.metadata.name

    command = (
        ["sh", "-c", f"echo 'rawfile' > /{pvc_name}/file.txt"]
        if pvc.spec.volume_mode == "Filesystem"
        else ["sh", "-c", f"echo 'rawfile' > /{pvc_name}"]
    )

    logger.info(f"Creating POD: {name}/{infinite}")
    body = client.V1Pod(
        metadata=client.V1ObjectMeta(name=name),
        spec=client.V1PodSpec(
            restart_policy="OnFailure",
            termination_grace_period_seconds=0,
            containers=[
                client.V1Container(
                    name=name,
                    image="busybox",
                    image_pull_policy="IfNotPresent",
                    command=command if not infinite else ["tail", "-f", "/dev/null"],
                    volume_mounts=[
                        client.V1VolumeMount(mount_path=f"/{pvc_name}", name=pvc_name)
                    ]
                    if pvc.spec.volume_mode == "Filesystem"
                    else [],
                    volume_devices=[
                        client.V1VolumeDevice(
                            device_path=f"/dev/{pvc_name}", name=pvc_name
                        )
                    ]
                    if pvc.spec.volume_mode == "Block"
                    else [],
                    security_context=client.V1SecurityContext(privileged=True),
                ),
            ],
            volumes=[
                client.V1Volume(
                    name=pvc_name,
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=pvc_name
                    ),
                )
            ],
        ),
    )
    return client.CoreV1Api().create_namespaced_pod(namespace, body)


@retry(
    stop_max_attempt_number=200,
    wait_fixed=100,
)
def wait_snapshot_deleted(name):
    global attempt_counter
    attempt_counter += 1
    try:
        client.CustomObjectsApi().get_namespaced_custom_object(
            group="snapshot.storage.k8s.io",
            version="v1",
            namespace=namespace,
            plural="volumesnapshots",
            name=name,
        )
        message = f"Snapshot {name} not deleted yet"
        if attempt_counter % 5 == 0:
            logger.debug(message)
        raise Exception(message)
    except ApiException as e:
        if e.status != 404:
            raise


@when(
    parsers.parse(
        "I create a Persistent Volume Claim with {copy_on_write} {fsfreeze} as source PVC"
    ),
    target_fixture="source_pvc",
)
def _(copy_on_write, fsfreeze):
    _copy_on_write = str_to_bool(copy_on_write)
    _fsfreeze = str_to_bool(fsfreeze)
    mix = f"{'cow' if _copy_on_write else 'no-cow'}-{'freeze' if _fsfreeze else 'no-freeze'}"
    pvc_name = f"pvc-{mix}"
    logger.info(f"Creating PVC: {pvc_name}")

    sc_name = f"sc-{mix}"
    sc = client.V1StorageClass(
        metadata=client.V1ObjectMeta(name=sc_name),
        provisioner=provisioner,
        volume_binding_mode="WaitForFirstConsumer",
        allow_volume_expansion=True,
        parameters={"copyOnWrite": copy_on_write, "freezeFs": fsfreeze},
    )
    stor_v1 = client.StorageV1Api()
    try:
        stor_v1.delete_storage_class(name=sc_name)
    except ApiException as e:
        if e.status != 404:
            raise
    stor_v1.create_storage_class(body=sc)

    pvc = client.V1PersistentVolumeClaim(
        metadata=client.V1ObjectMeta(
            name=pvc_name,
            annotations={
                "rawfile-test/clone-in-use": str(_copy_on_write or _fsfreeze).lower()
            },
        ),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=client.V1ResourceRequirements(requests={"storage": "512Mi"}),
            volume_mode="Filesystem",
            storage_class_name=sc_name,
        ),
    )
    core_v1 = client.CoreV1Api()
    pvc = core_v1.create_namespaced_persistent_volume_claim(
        body=pvc, namespace=namespace
    )
    yield pvc
    if not fixture_cleanup():
        return
    logger.info(f"Deleting PVC: {pvc_name}")
    stor_v1.delete_storage_class(name=sc_name)
    try:
        core_v1.delete_namespaced_persistent_volume_claim(
            name=pvc_name, namespace=namespace
        )
        wait_pvc_deleted(pvc_name)
    except ApiException as e:
        if e.status != 404:
            raise


@then("we create a pod which mounts the PVC", target_fixture="source_writer_pod")
def _(source_pvc):
    """we create a pod which mounts the PVC."""
    pod = create_pod(f"writer-{source_pvc.metadata.name}", source_pvc, True)
    yield pod
    if not fixture_cleanup():
        return
    name = pod.metadata.name
    logger.info(f"Deleting Snapshot POD: {name}")
    try:
        client.CoreV1Api().delete_namespaced_pod(name, namespace)
    except ApiException as e:
        if e.status != 404:
            raise
    wait_pod_deleted(name)


@then("we write some data to the mount path")
def _(source_pvc, source_writer_pod):
    """we write some data to the mount path."""
    pvc_name = source_pvc.metadata.name
    pod_name = source_writer_pod.metadata.name
    wait_pod_running(pod_name)
    exec_command = [
        "/bin/sh",
        "-c",
        f"i=1; while [ $i != 11 ]; do echo $i >> /{pvc_name}/file; i=$((i+1)); done; sync",
    ]
    stream(
        client.CoreV1Api().connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=exec_command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
    )


@then("delete pod if cloning of inused volume is disabled")
def _(source_writer_pod, source_pvc):
    """delete pod if snapshotting of inused volume is disabled."""
    pod_name = source_writer_pod.metadata.name
    if str_to_bool(
        source_pvc.metadata.annotations.get("rawfile-test/clone-in-use", "false")
    ):
        logger.info(
            f"Skipping deletion of source writer POD: {pod_name}, we are allowed to clone in used volumes"
        )
    else:
        try:
            logger.info(f"Deleting writer POD: {pod_name}")
            client.CoreV1Api().delete_namespaced_pod(pod_name, namespace)
        except ApiException as e:
            if e.status != 404:
                raise
        wait_pod_deleted(pod_name)


@when("we create a snapshot referencing the PVC", target_fixture="snapshot")
def _(source_pvc):
    """we create a snapshot referencing the PVC."""
    snap_class = "snapshot-class"
    snap_name = f"{source_pvc.metadata.name}-snap"
    try:
        client.CustomObjectsApi().delete_cluster_custom_object(
            group="snapshot.storage.k8s.io",
            version="v1",
            plural="volumesnapshotclasses",
            name=snap_class,
        )
    except ApiException as e:
        if e.status != 404:
            raise
    body = {
        "apiVersion": "snapshot.storage.k8s.io/v1",
        "kind": "VolumeSnapshotClass",
        "metadata": client.V1ObjectMeta(name=snap_class),
        "driver": provisioner,
        "deletionPolicy": "Delete",
    }
    logger.info(f"Creating Snapshot Class: {snap_class}")
    client.CustomObjectsApi().create_cluster_custom_object(
        group="snapshot.storage.k8s.io",
        version="v1",
        plural="volumesnapshotclasses",
        body=body,
    )
    logger.info(f"Created Snapshot Class: {snap_class}")
    snapshot = {
        "apiVersion": "snapshot.storage.k8s.io/v1",
        "kind": "VolumeSnapshot",
        "metadata": {"name": snap_name, "namespace": namespace},
        "spec": {
            "volumeSnapshotClassName": snap_class,
            "source": {"persistentVolumeClaimName": source_pvc.metadata.name},
        },
    }
    logger.info(f"Creating Snapshot: {snap_name}")
    snapshot = client.CustomObjectsApi().create_namespaced_custom_object(
        group="snapshot.storage.k8s.io",
        version="v1",
        namespace=namespace,
        plural="volumesnapshots",
        body=snapshot,
    )
    logger.info(f"Created Snapshot: {snap_name}")
    yield snapshot
    if not fixture_cleanup():
        return
    logger.debug(f"Deleting Snapshot Class: {snap_class}")
    client.CustomObjectsApi().delete_cluster_custom_object(
        group="snapshot.storage.k8s.io",
        version="v1",
        plural="volumesnapshotclasses",
        name=snap_class,
    )
    try:
        logger.debug(f"Deleting Snapshot: {snap_name}")
        client.CustomObjectsApi().delete_namespaced_custom_object(
            group="snapshot.storage.k8s.io",
            version="v1",
            namespace=namespace,
            plural="volumesnapshots",
            name=snap_name,
        )
        wait_snapshot_deleted(snap_name)
    except ApiException as e:
        if e.status != 404:
            raise


@then("the snapshot is eventually ready")
def _(snapshot):
    """the snapshot is eventually ready."""
    wait_snap_ready(snapshot["metadata"]["name"])


@when("we create a restore volume from the snapshot", target_fixture="restore_pvc")
def _(source_pvc, snapshot):
    """we create a restore volume from the snapshot."""
    data_source = client.V1TypedLocalObjectReference(
        api_group="snapshot.storage.k8s.io",
        kind="VolumeSnapshot",
        name=snapshot["metadata"]["name"],
    )
    pvc_name = f"{snapshot['metadata']['name']}-restore"
    restore_pvc = client.V1PersistentVolumeClaim(
        metadata=client.V1ObjectMeta(name=pvc_name),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=client.V1ResourceRequirements(requests={"storage": "512Mi"}),
            storage_class_name=source_pvc.spec.storage_class_name,
            data_source=data_source,
        ),
    )
    logger.info(f"Creating Restore PVC: {pvc_name}")
    core_v1 = client.CoreV1Api()
    restore_pvc = core_v1.create_namespaced_persistent_volume_claim(
        body=restore_pvc, namespace=namespace
    )
    yield restore_pvc
    if not fixture_cleanup():
        return
    logger.info(f"Deleting Restore PVC: {pvc_name}")
    try:
        core_v1.delete_namespaced_persistent_volume_claim(
            name=pvc_name, namespace=namespace
        )
        wait_pvc_deleted(pvc_name)
    except ApiException as e:
        if e.status != 404:
            raise


@when("we create a pod which mounts the restore PVC", target_fixture="restore_pod")
def _(restore_pvc):
    pod = create_pod(f"restore-{restore_pvc.metadata.name}", restore_pvc, True)
    yield pod
    if not fixture_cleanup():
        return
    name = pod.metadata.name
    logger.info(f"Deleting POD: {name}")
    try:
        client.CoreV1Api().delete_namespaced_pod(name, namespace)
    except ApiException as e:
        if e.status != 404:
            raise
    wait_pod_deleted(name)


@then("the restored volume should contain the snapshot data")
def _(restore_pvc, restore_pod):
    """the restored volume should contain the snapshot data."""
    pvc_name = restore_pvc.metadata.name
    pod_name = restore_pod.metadata.name
    wait_pod_running(pod_name)
    exec_command = [
        "/bin/sh",
        "-c",
        f"cat /{pvc_name}/file",
    ]
    out = stream(
        client.CoreV1Api().connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=exec_command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
    )
    # todo: aren't we missing the check for correct data here!?
    logger.info(f"cat /{pvc_name}/file => {out}")


@when("we delete the snapshot")
def _(snapshot):
    """we delete the snapshot."""
    snap_name = snapshot["metadata"]["name"]
    logger.info(f"Deleting Snapshot: {snap_name}")
    client.CustomObjectsApi().delete_namespaced_custom_object(
        group="snapshot.storage.k8s.io",
        version="v1",
        namespace=namespace,
        plural="volumesnapshots",
        name=snap_name,
    )


@then("snapshot should be eventually be deleted")
def _(snapshot):
    """snapshot should be eventually be deleted."""
    wait_snapshot_deleted(snapshot["metadata"]["name"])
    logger.info(f"Snapshot deleted: {snapshot['metadata']['name']}")


@when("we create a PVC that uses source PVC", target_fixture="clone_pvc")
def _(source_pvc):
    """we create a restore volume from the snapshot."""
    data_source = client.V1TypedLocalObjectReference(
        api_group="",
        kind="PersistentVolumeClaim",
        name=source_pvc.metadata.name,
    )
    pvc_name = f"{source_pvc.metadata.name}-clone"
    clone_pvc = client.V1PersistentVolumeClaim(
        metadata=client.V1ObjectMeta(name=pvc_name),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=client.V1ResourceRequirements(requests={"storage": "512Mi"}),
            storage_class_name=source_pvc.spec.storage_class_name,
            data_source=data_source,
        ),
    )
    logger.info(f"Creating Clone PVC: {pvc_name}")
    core_v1 = client.CoreV1Api()
    clone_pvc = core_v1.create_namespaced_persistent_volume_claim(
        body=clone_pvc, namespace=namespace
    )
    yield clone_pvc
    if not fixture_cleanup():
        return
    logger.info(f"Deleting Clone PVC: {pvc_name}")
    try:
        core_v1.delete_namespaced_persistent_volume_claim(
            name=pvc_name, namespace=namespace
        )
        wait_pvc_deleted(pvc_name)
    except ApiException as e:
        if e.status != 404:
            raise


@when("we create a pod which mounts the cloned PVC", target_fixture="clone_pod")
def _(clone_pvc):
    pod = create_pod(f"clone-{clone_pvc.metadata.name}", clone_pvc, True)
    yield pod
    if not fixture_cleanup():
        return
    name = pod.metadata.name
    logger.info(f"Deleting POD: {name}")
    try:
        client.CoreV1Api().delete_namespaced_pod(name, namespace)
    except ApiException as e:
        if e.status != 404:
            raise
    wait_pod_deleted(name)


@then("the newly created volume should contain the source data")
def _(clone_pvc, clone_pod):
    """the newly created volume should contain the source data."""
    pvc_name = clone_pvc.metadata.name
    pod_name = clone_pod.metadata.name
    wait_pod_running(pod_name)
    exec_command = [
        "/bin/sh",
        "-c",
        f"cat /{pvc_name}/file",
    ]
    out = stream(
        client.CoreV1Api().connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=exec_command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
    )
    logger.error(f"C: {out}")


@when("we delete the source PVC")
def _(source_pvc):
    """we delete the source PVC."""
    pvc_name = source_pvc.metadata.name
    logger.info(f"Deleting PVC: {pvc_name}")
    core_v1 = client.CoreV1Api()
    try:
        core_v1.delete_namespaced_persistent_volume_claim(
            name=pvc_name, namespace=namespace
        )
    except ApiException as e:
        if e.status != 404:
            raise


@then("source PVC should be eventually be deleted")
def _(source_pvc):
    """source PVC should be eventually be deleted."""
    wait_pvc_deleted(source_pvc.metadata.name)
    logger.info(f"PVC deleted: {source_pvc.metadata.name}")


@when("we delete the cloned PVC")
def _(clone_pvc):
    """we delete the cloned PVC."""
    pvc_name = clone_pvc.metadata.name
    logger.info(f"Deleting PVC: {pvc_name}")
    core_v1 = client.CoreV1Api()
    try:
        core_v1.delete_namespaced_persistent_volume_claim(
            name=pvc_name, namespace=namespace
        )
    except ApiException as e:
        if e.status != 404:
            raise


@then("cloned PVC should be eventually be deleted")
def _(clone_pvc):
    """clone PVC should be eventually be deleted."""
    wait_pvc_deleted(clone_pvc.metadata.name)
    logger.info(f"PVC deleted: {clone_pvc.metadata.name}")


@when("we delete the source writer pod")
def _(source_writer_pod):
    """we delete the source writer pod."""
    pod_name = source_writer_pod.metadata.name
    logger.info(f"Deleting POD: {pod_name}")
    core_v1 = client.CoreV1Api()
    try:
        core_v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
    except ApiException as e:
        if e.status != 404:
            raise


@then("source writer pod should be eventually be deleted")
def _(source_writer_pod):
    """source writer pod should be eventually be deleted."""
    wait_pod_deleted(source_writer_pod.metadata.name)
    logger.info(f"PVC deleted: {source_writer_pod.metadata.name}")


@when("we delete the clone pod")
def _(clone_pod):
    """we delete the clone pod."""
    pod_name = clone_pod.metadata.name
    logger.info(f"Deleting POD: {pod_name}")
    core_v1 = client.CoreV1Api()
    try:
        core_v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
    except ApiException as e:
        if e.status != 404:
            raise


@then("clone pod should be eventually be deleted")
def _(clone_pod):
    """clone PVC should be eventually be deleted."""
    wait_pod_deleted(clone_pod.metadata.name)
    logger.info(f"POD deleted: {clone_pod.metadata.name}")
