Feature: Basic Functionality

  Scenario Outline: Create PVCs with different storage parameters
    Given a Kubernetes cluster with rawfile-localpv installed
    When I create a Persistent Volume Claim with <binding_mode> <access_mode> <fs_type> <volume_mode>
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
    | binding_mode         | access_mode   | fs_type | volume_mode |
    | Immediate            | ReadWriteOnce | ext4    | Filesystem  |
    | Immediate            | ReadWriteOnce | xfs     | Filesystem  |
    | Immediate            | ReadWriteOnce | btrfs   | Filesystem  |
    | Immediate            | ReadWriteOnce | null    | Block       |
    | WaitForFirstConsumer | ReadWriteOnce | ext4    | Filesystem  |
    | WaitForFirstConsumer | ReadWriteOnce | null    | Block       |
