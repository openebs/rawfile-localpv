Feature: Basic Functionality

  Background:
    Given a Kubernetes cluster with rawfile-localpv installed

  Scenario Outline: Create PVCs with different storage parameters
    When I create a Persistent Volume Claim with <binding_mode> <access_mode> <fs_type> <volume_mode> <mount_options>
    Then the PVC should be bound if Binding mode is Immediate
    When a pod is created with the above PVC
    Then the PVC should be bound
    And the pod should complete with success
    When the PVC is expanded
    Then the Block PVCs status reflect the expanded size
    And the Filesystem PVC is pending node expansion
    When another pod is created with the above PVC
    Then the PVC status reflects the expanded size
    And the POD sees the expanded size

    Examples:
      | binding_mode         | access_mode   | fs_type | volume_mode | mount_options |
      | Immediate            | ReadWriteOnce | ext4    | Filesystem  | noatime       |
      | Immediate            | ReadWriteOnce | xfs     | Filesystem  | inode64       |
      | Immediate            | ReadWriteOnce | btrfs   | Filesystem  | null          |
      | Immediate            | ReadWriteOnce | null    | Block       | null          |
      | WaitForFirstConsumer | ReadWriteOnce | ext4    | Filesystem  | null          |
      | WaitForFirstConsumer | ReadWriteOnce | null    | Block       | null          |

  Scenario Outline: Snapshot creates and restores with different parameters and successfully remove it
    When I create a Persistent Volume Claim with <copy_on_write> <fsfreeze> as source PVC
    Then we create a pod which mounts the PVC
    And we write some data to the mount path
    And delete pod if cloning of inused volume is disabled
    When we create a snapshot referencing the PVC
    Then the snapshot is eventually ready
    And we overwrite the source volume with different data
    When we create a restore volume from the snapshot
    And we create a pod which mounts the restore PVC
    Then the restored volume should contain the snapshot data
    When we delete the source writer pod
    Then source writer pod should be eventually be deleted
    When we delete the source PVC
    Then source PVC should be eventually be deleted
    When we delete the snapshot
    Then snapshot should be eventually be deleted

    Examples:
      | copy_on_write | fsfreeze |
      | false         | false    |
      | true          | false    |
      | false         | true     |

  Scenario Outline: Create PVCs and use them as source for other PVCs
    When I create a Persistent Volume Claim with <copy_on_write> <fsfreeze> as source PVC
    Then we create a pod which mounts the PVC
    And we write some data to the mount path
    And delete pod if cloning of inused volume is disabled
    When we create a PVC that uses source PVC
    And we create a pod which mounts the cloned PVC
    Then the newly created volume should contain the source data
    When we delete the source writer pod
    Then source writer pod should be eventually be deleted
    When we delete the source PVC
    Then source PVC should be eventually be deleted
    When we delete the clone pod
    Then clone pod should be eventually be deleted
    When we delete the cloned PVC
    Then cloned PVC should be eventually be deleted

    Examples:
      | copy_on_write | fsfreeze |
      | false         | false    |
      | true          | false    |
      | false         | true     |
