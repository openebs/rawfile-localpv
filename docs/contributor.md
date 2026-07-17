# Contributing to Rawfile LocalPV

This guide will walk you through the process of building and testing rawfile using [nix] and [kind].

Rawfile is a sub-project of [OpenEBS][github-openebs], so don't forget to checkout the [umbrella contributor guide](https://github.com/openebs/community/blob/HEAD/CONTRIBUTING.md).

## Table of Contents

- [Contributing to Rawfile LocalPV](#contributing-to-rawfile-localpv)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
    - [System Packages](#system-packages)
    - [Development Shell](#development-shell)
  - [Building the images](#building-the-images)
  - [Deploying to K8s](#deploying-to-k8s)
    - [kind](#kind)
    - [NixOs-Shell Virtual Machine](#nixos-shell-virtual-machine)
  - [Installing](#installing)
    - [Official helm package](#official-helm-package)
    - [Local](#local)
  - [Testing](#testing)
    - [BDD tests](#bdd-tests)
    - [E2E tests](#e2e-tests)
  - [Commiting Code](#commiting-code)
  - [CI](#ci)
    - [GitHub Actions](#github-actions)
    - [🚀 Mergify IO Commands](#-mergify-io-commands)

## Prerequisites

Rawfile **only** builds modern Linuxes.

If you do not have a Linux system:

- **Windows:** You can try to use [WSL2][windows-wsl2]. Please let us know how you get on with this!
- **Mac:** We recommend you use [Docker for Mac][docker-install]
  and follow the Docker process described.
- **Others:** This is kind of a "do-it-yourself" situation. Sorry, we can't be more help!

### System Packages

You need to have a docker service installed on your local host/development machine. Docker is required for building rawfile container images and to push them into a Kubernetes cluster for testing.
The host/development machine must also run a local single node kubernetes cluster in order to run the ci tests.
But don't worry if this is not possible, raising a PR with the rawfile-locapv repository will run the tests for your changes against a [kind] cluster.

> [!NOTE]
> If you don't have docker installed, you may use the virtual machine through nixos-shell which comes
> packaged with docker and a kubernetes K3 cluster.
> More details on this later.

### Development Shell

The only thing your system needs to build Rawfile is [**Nix**][nix-install].

Usually [Nix][nix-install] can be installed via (Do **not** use `sudo`!):

```bash
curl -L https://nixos.org/nix/install | sh
```

But you should check the up-to-date documentation from [Nix][nix-install].
Entering a shell with all the required packages is rather simple, simply with `nix-shell`:

```console
> nix-shell
Using virtualenv: /Users/tiagocastro/Library/Caches/pypoetry/virtualenvs/rawfile-MvDqJOgK-py3.14
Installing dependencies from lock file

No dependencies to install or update

Installing the current project: rawfile (0.10.0)
pre-commit installed at .git/hooks/pre-commit
(rawfile-py3.14)
>
```

And there you have, the `python` virtual environment and the container build packages are all ready for you.
You can run `rawfile` directly if you want to:

```console
> cd rawfile
> ./rawfile.py csi-driver --endpoint unix:///tmp/csi.sock
> ...
```

> [!TIP]
You can keep using your favorite shell by running it, example: `nix-shell --run zsh`.

## Building the images

We have a `Dockerfile` containing the instructions required for building the rawfile container images.
To make things easier, we provide a script which sets up any necessary environment variables, call out the
docker commands, etc...

First you should enter the `nix-shell` and we've shown in the prequisites.
Once you're inside the shell, you can instantiate the image build script:

```console
> nix-shell
...
> .ci/build.sh
....
+ docker buildx build -t docker.io/openebs/rawfile-localpv:c46e819-ci --output=type=docker --platform=local --build-arg IMAGE_REPOSITORY=openebs/rawfile-localpv --build-arg IMAGE_TAG=c46e819 .ci/..
[+] Building 77.2s (18/18) FINISHED                                                                                                                                                                          docker-container:container-builder
 => [internal] load build definition from Dockerfile                                                                                                                                                         0.0s
 => => transferring dockerfile: 1.48kB                                                                                                                                                                       0.0s
 => [internal] load metadata for docker.io/library/python:3.13-slim-bookworm                                                                                                                                 0.8s
 => [internal] load .dockerignore                                                                                                                                                                            0.0s
 => => transferring context: 103B                                                                                                                                                                            0.0s
 => [internal] load build context                                                                                                                                                                            0.1s
 => => transferring context: 364.22kB                                                                                                                                                                        0.1s
 => CACHED [base 1/2] FROM docker.io/library/python:3.13-slim-bookworm@sha256:6544e0e002b40ae0f59bc3618b07c1e48064c4faed3a15ae2fbd2e8f663e8283                                                               0.1s
 => => resolve docker.io/library/python:3.13-slim-bookworm@sha256:6544e0e002b40ae0f59bc3618b07c1e48064c4faed3a15ae2fbd2e8f663e8283                                                                           0.0s
 => [base 2/2] RUN apt-get update &&     apt-get install -y     btrfs-progs     libbtrfsutil-dev     e2fsprogs     btrfs-progs     xfsprogs     gcc                                                          31.7s
 => [builder-base 1/5] RUN apt-get update     && apt-get install --no-install-recommends -y     curl     build-essential                                                                                     9.2s
 => [builder-base 2/5] RUN curl -sSL https://install.python-poetry.org | python3 -                                                                                                                           13.8s
 => [builder-base 3/5] WORKDIR /opt/pysetup                                                                                                                                                                  0.1s
 => [builder-base 4/5] COPY ./poetry.lock ./pyproject.toml ./                                                                                                                                                0.1s
 => [builder-base 5/5] RUN poetry install --only main --no-root                                                                                                                                              4.1s
 => [production 1/5] COPY --from=builder-base /opt/pysetup/.venv /opt/pysetup/.venv                                                                                                                          0.4s
 => [production 2/5] COPY ./rawfile /rawfile                                                                                                                                                                 0.1s
 => [production 3/5] WORKDIR /rawfile                                                                                                                                                                        0.1s
 => [production 4/5] RUN python -m     grpc_tools.protoc     --proto_path=protos/     protos/csi.proto     --grpc_python_out=csi/     --python_out=csi/ &&     python utils/fallocate/build.py               1.2s
 => [production 5/5] COPY docker-entrypoint.sh /docker-entrypoint.sh                                                                                                                                         0.1s
 => exporting to docker image format                                                                                                                                                                         15.1s
 => => exporting layers                                                                                                                                                                                      10.3s
 => => exporting manifest sha256:b741eafdc877b974dde87adb2a49c9e3ebb48a58d1b8db9746f56c66e28c614c                                                                                                            0.0s
 => => exporting config sha256:d56e4db960f8768447f1be43dc20385bedb313e5c80f24439e20e9a3e173122b                                                                                                              0.0s
 => => sending tarball                                                                                                                                                                                       4.7s
 => importing to docker                                                                                                                                                                                      3.8s
 => => loading layer 344b8d92c7ef 129.45MB / 129.45MB                                                                                                                                                        3.8s
 => => loading layer f84a628ec573 15.78MB / 15.78MB                                                                                                                                                          0.9s
 => => loading layer 1453bf5ef3aa 180.12kB / 180.12kB                                                                                                                                                        0.3s
 => => loading layer 5f70bf18a086 32B / 32B                                                                                                                                                                  0.2s
 => => loading layer c19b1c34f508 22.79kB / 22.79kB                                                                                                                                                          0.1s
 => => loading layer 16f3a49e3b07 205B / 205B                                                                                                                                                                0.1s
++ kubectl config current-context
+ '[' kind-kind = kind-rawfile ']'
```

Now that you are familiar with [nix], you should now that most scripts have dependencies which are handled via
the [nix] development shell, so you don't need to worry about it.
From now on you should assume that you must enter the `nix-shell` for every script or command.

> [!NOTE]
> If the [kind] test cluster is up, the images will be automatically pushed

## Deploying to K8s

When you're mostly done with a set of changes, you'll want to test them in a K8s cluster. For this let's assume you've already built the container images, as shown in the above step.

We suggest a few options for this:

- [kind]
- [nixos-shell]
- [K3d]
- [minikube]

### [kind]

[kind] is a tool for running local Kubernetes clusters using Docker container "nodes".
To use kind, you will also need to install docker on your host, as mentioned in the [prerequisites](#system-packages).

You don't have to install [kind] yourself, since we bundle it with the [nix-shell](../shell.nix).

```console
> .ci/deployer.sh start
Deleting cluster "rawfile" ...
Creating cluster "rawfile" ...
 ✓ Ensuring node image (kindest/node:v1.33.1) 🖼
 ✓ Preparing nodes 📦 📦
 ✓ Writing configuration 📜
 ✓ Starting control-plane 🕹
 ✓ Installing CNI 🔌
 ✓ Installing StorageClass 💾
 ✓ Joining worker nodes 🚜
Set kubectl context to "kind-rawfile"
You can now use your cluster with:

kubectl cluster-info --context kind-rawfile

Have a question, bug, or feature request? Let us know! https://kind.sigs.k8s.io/#community 🙂
Kubernetes control plane is running at https://127.0.0.1:38657
CoreDNS is running at https://127.0.0.1:38657/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
HostIP: 172.18.0.1

WARNING: apt does not have a stable CLI interface. Use with caution in scripts.

Get:1 http://deb.debian.org/debian bookworm InRelease [151 kB]
Get:2 http://deb.debian.org/debian bookworm-updates InRelease [55.4 kB]
Get:3 http://deb.debian.org/debian-security bookworm-security InRelease [48.0 kB]
Get:4 http://deb.debian.org/debian bookworm/main amd64 Packages [8793 kB]
Get:5 http://deb.debian.org/debian bookworm-updates/main amd64 Packages [756 B]
Get:6 http://deb.debian.org/debian-security bookworm-security/main amd64 Packages [272 kB]
Fetched 9320 kB in 2s (4429 kB/s)
Reading package lists...
Building dependency tree...
Reading state information...
```

And there you have, a K8s cluster ready for development and very happy to be broken, since you can simply re-deploy it again:

```console
> .ci/deployer.sh start --cleanup
....
```

Once you're done with it, there's no point keeping it up and running, please tear it down and save some watts!

```console
> .ci/deployer.sh stop
Deleting cluster "rawfile" ...
Deleted nodes: ["rawfile-worker" "rawfile-control-plane"]
```

You can use `--help` for more parameter information.
This is left as a readers exercise.

### [NixOs-Shell] Virtual Machine

If you're already using [nix-shell], then why not take this option? \
How does it work? \
It spawns a headless qemu virtual machines based on a [configuration file](../vm.nix) and it provides console access in the same terminal window.

The provided [configuration file](../vm.nix) deploys as a single node [K3s] cluster with the required filesystem drivers and tools.

If you're already on the `nix-shell`, simply run it:

```console
> nixos-shell
evaluation warning: system.stateVersion is not set, defaulting to 25.05. Read why this matters on https://nixos.org/manual/nixos/stable/options.html#opt-system.stateVersion.
Disk image do not exist, creating the virtualisation disk image...
Formatting '/tmp/nix-shell-903087-0/tmp.w5DoLDOLcG', fmt=raw size=21474836480
mke2fs 1.47.2 (1-Jan-2025)
Discarding device blocks: done
Creating filesystem with 5242880 4k blocks and 1310720 inodes
Filesystem UUID: b099259f-af4f-4517-b8d0-a890e25bad8e
Superblock backups stored on blocks:
        32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208,
        4096000

Allocating group tables: done
Writing inode tables: done
Creating journal (32768 blocks): done
Writing superblocks and filesystem accounting information: done

Virtualisation disk image created.
running activation script...
setting up /etc...

Welcome to NixOS 25.05 (Warbler)!

[  OK  ] Created slice Slice /system/getty.
[  OK  ] Created slice Slice /system/modprobe.
[  OK  ] Created slice Slice /system/serial-getty.
[  OK  ] Created slice User and Session Slice.
[  OK  ] Started Dispatch Password Requests to Console Directory Watch.
[  OK  ] Started Forward Password Requests to Wall Directory Watch.
         Expecting device /dev/hvc0...
[  OK  ] Reached target Local Encrypted Volumes.
[  OK  ] Reached target Containers.
...
[  OK  ] Finished SSH Host Keys Generation.
[  OK  ] Started SSH Daemon.
[  OK  ] Started DHCP Client.
[  OK  ] Reached target Network is Online.
         Starting Docker Application Container Engine...
         Starting k3s service...
[  OK  ] Started Docker Application Container Engine.

<<< Welcome to NixOS 25.05.802746.7282cb574e06 (x86_64) - hvc0 >>>
If you are connect via serial console:
Type Ctrl-a c to switch to the qemu console
and `quit` to stop the VM.

Run 'nixos-help' for the NixOS manual.

nixos login: root (automatic login)
```

Since this is a k3s cluster, you should load built images into it, example:

```console
> docker save docker.io/openebs/rawfile-localpv:c46e819-ci | k3s ctr images import -
```

> **NOTE** Image name and tag is from the last build output, you can also use `docker images` to find out what you have locally.

To leave this shell you can use the key combination `Ctrl-a x`.
You can then enter the [nixos-shell] again using the same command.
Feel free to make irreparable damage to the virtual machine, simply delete it and start anew. This is as simple as:

```console
# Leave the vm terminal and run:
rm nixos.qcow2
nixos-shell
```

## Installing

### Official helm package

First you need to add the rawfile-localpv helm registry to your local system.

```console
> helm repo add rawfile-localpv https://openebs.github.io/rawfile-localpv
"rawfile-localpv" has been added to your repositories
```

Once that's done, you simply need to install it on your chosen namespace.

```console
> helm install rawfile-localpv rawfile-localpv/rawfile-localpv -n openebs --create-namespace --wait
NAME: rawfile-localpv
LAST DEPLOYED: Tue Jul 15 14:39:14 2025
NAMESPACE: openebs
STATUS: deployed
REVISION: 1
TEST SUITE: None
```

### Local

When developing or testing you'll want to install using your custom images and helm chart.
Once you've built the images as described above, you could simply use our e2e install script.

```console
> .ci/e2e-test/setup.sh
...
+ helm upgrade --wait -n openebs --create-namespace -i rawfile-localpv --set metrics.serviceMonitor.enabled=false --set image.registry=docker.io,image.repository=openebs/rawfile-localpv,image.tag=30765bf-ci,image.pullPolicy=Never --set logLevel=DEBUG,logFormat=pretty .ci/e2e-test/../../deploy/helm/rawfile-localpv/
Release "rawfile-localpv" does not exist. Installing it now.
NAME: rawfile-localpv
LAST DEPLOYED: Tue Jul 15 15:48:55 2025
NAMESPACE: openebs
STATUS: deployed
REVISION: 1
TEST SUITE: None
+ kubectl wait --for=condition=ready pod --all -n openebs
pod/rawfile-localpv-controller-0 condition met
pod/rawfile-localpv-node-8xscw condition met
+ kubectl get pods -n openebs -o wide
NAME                           READY   STATUS    RESTARTS   AGE   IP           NODE             NOMINATED NODE   READINESS GATES
rawfile-localpv-controller-0   2/2     Running   0          26s   10.244.1.3   rawfile-worker   <none>           <none>
rawfile-localpv-node-8xscw     5/5     Running   0          26s   10.244.1.2   rawfile-worker   <none>           <none>
```

> [!IMPORTANT]
> The setup.sh script deploys the local helm chart using the current git commit hash, so if you're committing code
> and rebuilding images, please be aware that you'll have to re-run the setup script!

## Testing

There are a few different types of tests used in rawfile-localpv:

- BDD smoke tests
- K8s E2E tests

### BDD tests

The BDD tests are currently only composed of smoke tests. In the future we may extend this.

To run the smoke tests, we've again provided a script.

```console
> .ci/smoke.sh
=================================================================================================================================================== test session starts ====================================================================================================================================================
platform linux -- Python 3.13.3, pytest-8.4.1, pluggy-1.6.0
rootdir: /home/tiago/git/openebs/rawfile-localpv/rawfile/tests
configfile: pytest.ini
plugins: bdd-8.1.0
collected 8 items

test_smoke.py::test_create_pvcs_with_different_storage_parameters[Immediate-ReadWriteOnce-ext4-Filesystem-noatime]
------------------------------------------------------------------------------------------------------------------------------------------------------ live log call -------------------------------------------------------------------------------------------------------------------------------------------------------
2025-07-15 16:08:21 [INFO] Running '['/nix/store/ih5m6g033nspbvg80hypv4aqpxgwrkjz-helm-3.17.3/bin/helm', 'ls', '-n', 'openebs', '--deployed', '--filter=^rawfile-localpv$', '-o=json']'
2025-07-15 16:08:21 [WARNING] Helm release 'rawfile-localpv' already exists in the 'openebs' namespace @ v0.10.0.
2025-07-15 16:08:21 [INFO] Prepping test namespace: rawfile-test
2025-07-15 16:08:26 [INFO] Creating PVC: pvc-im-rwo-ext4-fs-no
2025-07-15 16:08:26 [INFO] Skipping PVC pvc-im-rwo-ext4-fs-no as it won't bind till first use
2025-07-15 16:08:26 [INFO] Creating POD: pvc-im-rwo-ext4-fs-no/False
....
===================================================================================================================================================== warnings summary =====================================================================================================================================================
test_smoke.py: 977 warnings
  /home/tiago/.cache/pypoetry/virtualenvs/rawfile-xNvq-e8_-py3.14/lib/python3.13/site-packages/retrying.py:267: DeprecationWarning: The 'warn' method is deprecated, use 'warning' instead
    self._logger.warn(attempt)

test_smoke.py: 38 warnings
  /home/tiago/.cache/pypoetry/virtualenvs/rawfile-xNvq-e8_-py3.14/lib/python3.13/site-packages/kubernetes/client/rest.py:44: DeprecationWarning: HTTPResponse.getheaders() is deprecated and will be removed in urllib3 v2.6.0. Instead access HTTPResponse.headers directly.
    return self.urllib3_response.getheaders()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
------------------------------------------------------------------------------------------------------------------- generated xml file: /home/tiago/git/openebs/rawfile-localpv/rawfile/tests/report.xml -------------------------------------------------------------------------------------------------------------------
=================================================================================================================================================== slowest 20 durations ===================================================================================================================================================
33.67s call     test_smoke.py::test_create_pvcs_with_different_storage_parameters[Immediate-ReadWriteOnce-ext4-Filesystem-noatime]
31.86s call     test_smoke.py::test_create_pvcs_with_different_storage_parameters[Immediate-ReadWriteOnce-btrfs-Filesystem-null]
26.94s call     test_smoke.py::test_create_pvcs_with_different_storage_parameters[Immediate-ReadWriteOnce-xfs-Filesystem-inode64]
18.35s call     test_smoke.py::test_create_pvcs_with_different_storage_parameters[Immediate-ReadWriteOnce-null-Block-null]
17.71s call     test_smoke.py::test_create_pvcs_with_different_storage_parameters[WaitForFirstConsumer-ReadWriteOnce-ext4-Filesystem-null]
11.14s call     test_smoke.py::test_create_pvcs_with_different_storage_parameters[WaitForFirstConsumer-ReadWriteOnce-null-Block-null]
7.58s call     test_smoke.py::test_deleting_snapshot_of_unstaged_volume
4.04s call     test_smoke.py::test_butter_fs_snapshots_and_restores
1.04s teardown test_smoke.py::test_butter_fs_snapshots_and_restores
0.08s teardown test_smoke.py::test_create_pvcs_with_different_storage_parameters[WaitForFirstConsumer-ReadWriteOnce-null-Block-null]
0.08s teardown test_smoke.py::test_create_pvcs_with_different_storage_parameters[WaitForFirstConsumer-ReadWriteOnce-ext4-Filesystem-null]
0.08s teardown test_smoke.py::test_create_pvcs_with_different_storage_parameters[Immediate-ReadWriteOnce-ext4-Filesystem-noatime]
0.08s teardown test_smoke.py::test_create_pvcs_with_different_storage_parameters[Immediate-ReadWriteOnce-btrfs-Filesystem-null]
0.07s teardown test_smoke.py::test_create_pvcs_with_different_storage_parameters[Immediate-ReadWriteOnce-xfs-Filesystem-inode64]
0.07s teardown test_smoke.py::test_create_pvcs_with_different_storage_parameters[Immediate-ReadWriteOnce-null-Block-null]
0.05s teardown test_smoke.py::test_deleting_snapshot_of_unstaged_volume

(4 durations < 0.005s hidden.  Use -vv to show these durations.)
======================================================================================================================================= 8 passed, 1015 warnings in 153.28s (0:02:33) =======================================================================================================================================
```

Of course you can also simply use pytest directly. You can take a look at the [tests here](../rawfile/tests/).

### E2E tests

We don't have our own end-to-end tests, instead we make use of the [K8s storage tests](https://github.com/kubernetes/kubernetes/tree/master/test/e2e/storage/testsuites) using the ginkgo framework.

```console
> .ci/e2e-test/test.sh
++ cat .ci/e2e-test/../../.kube-version
+ K8S_VERSION=v1.33.1
+ K8S_CLUSTER=kind
+ DOWNLOAD=true
+ '[' -f .ci/e2e-test/e2e.test ']'
++ .ci/e2e-test/e2e.test -version
+ '[' v1.31.6 = v1.33.1 ']'
++ dirname .ci/e2e-test/test.sh
+ cd .ci/e2e-test
+ '[' true = true ']'
+ command -v curl
+ curl --location https://dl.k8s.io/v1.33.1/kubernetes-test-linux-amd64.tar.gz
+ tar --strip-components=3 --no-same-owner -zxf - kubernetes/test/bin/e2e.test kubernetes/test/bin/ginkgo
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   138  100   138    0     0    723      0 --:--:-- --:--:-- --:--:--   726
100 95.8M  100 95.8M    0     0  6537k      0  0:00:15  0:00:15 --:--:-- 7123k
+ '[' kind = kind ']'
+ export KUBE_SSH_USER=root
+ KUBE_SSH_USER=root
++ pwd
+ export KUBE_SSH_KEY=/home/tiago/git/openebs/rawfile-localpv/.ci/e2e-test/ssh_id
+ KUBE_SSH_KEY=/home/tiago/git/openebs/rawfile-localpv/.ci/e2e-test/ssh_id
+ '[' -z '' ']'
+ export KUBECONFIG=/home/tiago/.kube/config
+ KUBECONFIG=/home/tiago/.kube/config
+ ./ginkgo -p -v -focus=External.Storage '-skip=\[Feature:|\[Disruptive\]|\[Serial\]' --fail-fast ./e2e.test -- -storage.testdriver=rawfile-driver.yaml
Running Suite: Kubernetes e2e suite - /home/tiago/git/openebs/rawfile-localpv/.ci/e2e-test
==========================================================================================
Random Seed: 1752592885 - will randomize all specs

Will run 179 of 7035 specs
Running in parallel across 15 processes
------------------------------
[ReportBeforeSuite] PASSED [0.001 seconds]
[ReportBeforeSuite]
k8s.io/kubernetes/test/e2e/e2e_test.go:153
------------------------------
[SynchronizedBeforeSuite] PASSED [0.032 seconds]
[SynchronizedBeforeSuite]
......

Ran 11 of 7035 Specs in 445.969 seconds
SUCCESS! -- 11 Passed | 0 Failed | 0 Pending | 7024 Skipped
PASS

Ginkgo ran 1 suite in 7m26.589936387s
Test Suite Passed
```

These tests may take some time to run (~20 minutes at the time of writing).

## Commiting Code

If you're commiting code, please be aware we have git [pre-commit] hooks in place which should help you prepare
your changes by linting your code, re-generating helm documentation, etc.

Here's an example where I'm trying to commit some docs

```console
> git commit -sS
[INFO] Stashing unstaged files to /Users/tiagocastro/.cache/pre-commit/patch1752447125-23869.
[INFO] Initializing environment for https://github.com/astral-sh/ruff-pre-commit.
[INFO] Initializing environment for https://github.com/norwoodj/helm-docs.
[INFO] Installing environment for https://github.com/astral-sh/ruff-pre-commit.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
[INFO] Installing environment for https://github.com/norwoodj/helm-docs.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
ruff (legacy alias)..................................(no files to check)Skipped
ruff format..........................................(no files to check)Skipped
check yaml...........................................(no files to check)Skipped
fix end of files.........................................................Passed
trim trailing whitespace.................................................Failed
- hook id: trailing-whitespace
- exit code: 1
- files were modified by this hook

Fixing docs/develop.md

Helm Docs Built......................................(no files to check)Skipped
```

In this case, if you're happy with the changes, simply re-stage and attempt commit again, example:

```console
> git add docs
> git commit -s
[INFO] Stashing unstaged files to /Users/tiagocastro/.cache/pre-commit/patch1752447398-25108.
ruff (legacy alias)..................................(no files to check)Skipped
ruff format..........................................(no files to check)Skipped
check yaml...........................................(no files to check)Skipped
fix end of files.........................................................Passed
trim trailing whitespace.................................................Passed
Helm Docs Built......................................(no files to check)Skipped
[INFO] Restored changes from /Users/tiagocastro/.cache/pre-commit/patch1752447398-25108.
[docs 7631ca0] docs: add developer documentation
 1 file changed, 297 insertions(+)
 create mode 100644 docs/develop.md
```

You might have noticed in the examples above I commited with `-s`. \
Please ensure you always do so. See more information on the [contributing guide](https://github.com/openebs/community/blob/develop/CONTRIBUTING.md#sign-your-work).

## CI

Our CI system is based on [mergify] and [GitHub Actions][github-actions].

### GitHub Actions

For the GitHub Actions you can refer to the `./github/workflows` folder.

As things stand, all test actions run when a PR is created/updated. The [mergify] bot is only used for easier
merging of a PR, automatically rebasing and re-running the tests if necessary.

### 🚀 Mergify IO Commands

Use these commands directly in your GitHub pull request comments to automate actions with Mergify.

| Command                | Description                                          |
|------------------------|------------------------------------------------------|
| `@Mergifyio rebase`    | Rebase the pull request onto its base branch         |
| `@Mergifyio refresh`   | Refresh Mergify’s status checks                      |
| `@Mergifyio update`    | Merge the base branch into the pull request          |
| `@Mergifyio squash`    | Squash all commits in the pull request               |
| `@Mergifyio backport`  | Copy the pull request to another branch after merge  |
| `@Mergifyio copy`      | Copy the pull request to another branch              |
| `@Mergifyio queue`     | Add the pull request to a merge queue                |
| `@Mergifyio dequeue`   | Remove the pull request from a merge queue           |
| `@Mergifyio requeue`   | Re-enter the pull request into the merge queue       |

> [!NOTE]
> We're still getting familiar with mergify ourselves, so if you have any improvements or suggestion
> on how we can leverage it better, we'd be delighted to hear about it!

[nix]: https://nixos.org/
[kind]: https://kind.sigs.k8s.io/
[nix-shell]: https://nixos.org/manual/nix/unstable/command-ref/new-cli/nix3-shell.html
[nixos-shell]: https://github.com/Mic92/nixos-shell
[windows-wsl2]: https://wiki.ubuntu.com/WSL#Ubuntu_on_WSL
[docker-install]: https://docs.docker.com/get-docker/
[nix-install]: https://nixos.org/download.html
[github-openebs]: https://github.com/openebs
[github-actions]: https://docs.github.com/en/actions
[mergify]: https://mergify.com/
[pre-commit]: https://pre-commit.com/
[minikube]: https://minikube.sigs.k8s.io/docs/
[K3d]: https://k3d.io/stable/
[K3s]: https://k3s.io/
