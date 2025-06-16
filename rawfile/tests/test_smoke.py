import pytest
from pytest_bdd import scenario, given, when, then, parsers
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from retrying import retry
from kubernetes.stream import stream
import logging
from common.helm import HelmReleaseClient
from common.k8s_deployer import Deployer
from common import fixture_cleanup

logger = logging.getLogger(__name__)
helm = HelmReleaseClient()
deployer = Deployer()

namespace = "rawfile-test"


@scenario("smoke.feature", "Create PVCs with different storage parameters")
def test_create_pvcs_with_different_storage_parameters():
    """Create PVCs with different storage parameters."""


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
            raise e
    wait_ns_deleted(namespace)
    api.create_namespace(body)


@given("a Kubernetes cluster with rawfile-localpv installed")
def _(cluster):
    """a Kubernetes cluster with rawfile-localpv installed."""
    pass


@when(
    parsers.parse(
        "I create a Persistent Volume Claim with {binding_mode} {access_mode} {fs_type} {volume_mode}"
    ),
    target_fixture="pvc",
)
def _(binding_mode, access_mode, fs_type, volume_mode):
    mix = f"{binding_mode}-{access_mode}-{fs_type}-{volume_mode}".lower()
    pvc_name = f"pvc-{mix}"
    logger.info(f"Creating PVC: {pvc_name}")

    sc_name = f"sc-{mix}"
    sc = client.V1StorageClass(
        metadata=client.V1ObjectMeta(name=sc_name),
        provisioner="rawfile.csi.openebs.io",
        volume_binding_mode=binding_mode,
        allow_volume_expansion=True,
        parameters={"csi.storage.k8s.io/fstype": fs_type},
    )
    stor_v1 = client.StorageV1Api()
    try:
        stor_v1.delete_storage_class(name=sc_name)
    except ApiException as e:
        if e.status != 404:
            raise e
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
    core_v1.delete_namespaced_persistent_volume_claim(
        name=pvc_name, namespace=namespace
    )
    wait_pvc_deleted(pvc_name)


@when("a pod is created with the above PVC", target_fixture="pod")
def _(pvc):
    """a pod is created with the above PVC."""
    pod = create_pod(pvc.metadata.name, pvc)
    yield pod
    if not fixture_cleanup():
        return
    name = pod.metadata.name
    logger.info(f"Deleting POD: {name}")
    client.CoreV1Api().delete_namespaced_pod(name, namespace)
    wait_pod_deleted(name)


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
            raise e
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
    pass


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
def _(pod):
    """the pod should complete with success."""
    wait_pod_success(pod.metadata.name)
    logger.info(f"Pod {pod.metadata.name} is complete")


@retry(
    stop_max_attempt_number=200,
    wait_fixed=100,
)
def wait_pod_success(name):
    pod = client.CoreV1Api().read_namespaced_pod(name, namespace)
    message = f"Pod {name} not completed yet"
    logger.debug(message)
    assert pod.status.phase == "Succeeded", message


@retry(
    stop_max_attempt_number=200,
    wait_fixed=100,
)
def wait_pod_running(name):
    pod = client.CoreV1Api().read_namespaced_pod(name, namespace)
    message = f"Pod {name} not completed yet"
    logger.debug(message)
    assert pod.status.phase == "Running", message


@retry(
    stop_max_attempt_number=200,
    wait_fixed=100,
)
def wait_pvc_bound(name):
    pvc = client.CoreV1Api().read_namespaced_persistent_volume_claim(name, namespace)
    message = f"PVC {name} not bound yet"
    logger.debug(message)
    assert pvc.status.phase == "Bound", message


@retry(
    stop_max_attempt_number=1000,
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
    try:
        client.CoreV1Api().read_namespace(name=namespace)
        message = f"Namespace {name} not deleted yet"
        logger.debug(message)
        raise Exception(message)
    except ApiException as e:
        if e.status != 404:
            raise e


@retry(
    stop_max_attempt_number=200,
    wait_fixed=100,
)
def wait_pvc_deleted(name):
    try:
        client.CoreV1Api().read_namespaced_persistent_volume_claim(name, namespace)
        message = f"PVC {name} not deleted yet"
        logger.debug(message)
        raise Exception(message)
    except ApiException as e:
        if e.status != 404:
            raise e


@retry(
    stop_max_attempt_number=200,
    wait_fixed=100,
)
def wait_pod_deleted(name):
    try:
        client.CoreV1Api().read_namespaced_pod(name, namespace)
        message = f"Pod {name} not deleted yet"
        logger.debug(message)
        raise Exception(message)
    except ApiException as e:
        if e.status != 404:
            raise e


def create_pod(name, pvc, sleep=False):
    pvc_name = pvc.metadata.name

    command = (
        ["sh", "-c", f"echo 'rawfile' > /{pvc_name}/file.txt"]
        if pvc.spec.volume_mode == "Filesystem"
        else ["sh", "-c", f"echo 'rawfile' > /{pvc_name}"]
    )

    logger.info(f"Creating POD: {name}/{sleep}")
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
                    command=command if not sleep else ["sh", "-c", "sleep infinity"],
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
