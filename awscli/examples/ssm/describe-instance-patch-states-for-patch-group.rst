**Example 1: To get the instance states for a patch group**

The following ``describe-instance-patch-states-for-patch-group`` example retrieves details about the patch summary states per-instance for the specified patch group. ::

    aws ssm describe-instance-patch-states-for-patch-group \
        --patch-group "Production"

Output::

    {
        "InstancePatchStates": [
            {
                "InstanceId": "i-02573cafcfEXAMPLE",
                "BaselineId": "pb-0c10e65780EXAMPLE",
                "SnapshotId": "a3f5ff34-9bc4-4d2c-a665-4d1c1EXAMPLE",
                "PatchGroup": "Production",
                "OwnerInformation": "",
                "FailedCount": 0,
                "InstalledCount": 17,
                "InstalledOtherCount": 378,
                "InstalledPendingRebootCount": 3,
                "InstalledRejectedCount": 1
                "MissingCount": 14,
                "UnreportedNotApplicableCount": 0,
                "NotApplicableCount": 396,
                "Operation": "Scan",
                "OperationEndTime": 1520964020,
                "OperationStartTime": 1520964019,
                "RebootOption": "RebootIfNeeded"
            },
            {
                "InstanceId": "i-0471e04240EXAMPLE",
                "BaselineId": "pb-09ca3fb51fEXAMPLE",
                "SnapshotId": "05d8ffb0-1bbe-4812-ba2d-d9b7bEXAMPLE",
                "PatchGroup": "Production",
                "OwnerInformation": "",
                "FailedCount": 0,
                "InstalledCount": 22,
                "InstalledOtherCount": 452,
                "InstalledPendingRebootCount": 4,
                "InstalledRejectedCount": 1,
                "MissingCount": 16,
                "UnreportedNotApplicableCount": 0,
                "NotApplicableCount": 401,
                "Operation": "Scan",
                "OperationEndTime": 1520964020,
                "OperationStartTime": 1520964019,
                "RebootOption": "RebootIfNeeded"
            }
        ]
    }

For more information, see `About Patch Compliance States <https://docs.aws.amazon.com/systems-manager/latest/userguide/about-patch-compliance-states.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To get the instance states for a patch group with more than five missing patches**

The following ``describe-instance-patch-states-for-patch-group`` example retrieves details about the patch summary states for the specified patch group for instances with more than five missing patches. ::

    aws ssm describe-instance-patch-states-for-patch-group \
        --filters Key=MissingCount,Type=GreaterThan,Values=5 \
        --patch-group "Production"

Output::

    {
        "InstancePatchStates": [
            {
                "InstanceId": "i-02573cafcfEXAMPLE",
                "BaselineId": "pb-0c10e65780EXAMPLE",
                "SnapshotId": "a3f5ff34-9bc4-4d2c-a665-4d1c1EXAMPLE",
                "PatchGroup": "Production",
                "OwnerInformation": "",
                "FailedCount": 0,
                "InstalledCount": 17,
                "InstalledOtherCount": 378,
                "InstalledPendingRebootCount": 3,
                "InstalledRejectedCount": 1
                "MissingCount": 14,
                "UnreportedNotApplicableCount": 0,
                "NotApplicableCount": 396,
                "Operation": "Scan",
                "OperationEndTime": 1520964020,
                "OperationStartTime": 1520964019,
                "RebootOption": "RebootIfNeeded"
            },
            {
                "InstanceId": "i-0471e04240EXAMPLE",
                "BaselineId": "pb-09ca3fb51fEXAMPLE",
                "SnapshotId": "05d8ffb0-1bbe-4812-ba2d-d9b7bEXAMPLE",
                "PatchGroup": "Production",
                "OwnerInformation": "",
                "FailedCount": 0,
                "InstalledCount": 22,
                "InstalledOtherCount": 452,
                "InstalledPendingRebootCount": 4,
                "InstalledRejectedCount": 1,
                "MissingCount": 16,
                "UnreportedNotApplicableCount": 0,
                "NotApplicableCount": 401,
                "Operation": "Scan",
                "OperationEndTime": 1520964020,
                "OperationStartTime": 1520964019,
                "RebootOption": "RebootIfNeeded"
            }
        ]
    }

For more information, see `About Patch Compliance States <https://docs.aws.amazon.com/systems-manager/latest/userguide/about-patch-compliance-states.html>`__ in the *AWS Systems Manager User Guide*.

**Example 3: To get the instance states for a patch group with fewer than ten instances that require a reboot**

The following ``describe-instance-patch-states-for-patch-group`` example retrieves details about the patch summary states for the specified patch group for instances with fewer than ten instances requiring a reboot. ::

    aws ssm describe-instance-patch-states-for-patch-group \
        --filters Key=InstalledPendingRebootCount,Type=LessThan,Values=10 \
        --patch-group "Production"

Output::

    {
        "InstancePatchStates": [
            {
                "InstanceId": "i-02573cafcfEXAMPLE",
                "BaselineId": "pb-0c10e65780EXAMPLE",
                "SnapshotId": "a3f5ff34-9bc4-4d2c-a665-4d1c1EXAMPLE",
                "PatchGroup": "Production",
                "OwnerInformation": "",
                "FailedCount": 0,
                "InstalledCount": 17,
                "InstalledOtherCount": 378,
                "InstalledPendingRebootCount": 3,
                "InstalledRejectedCount": 1
                "MissingCount": 14,
                "UnreportedNotApplicableCount": 0,
                "NotApplicableCount": 396,
                "Operation": "Scan",
                "OperationEndTime": 1520964020,
                "OperationStartTime": 1520964019,
                "RebootOption": "RebootIfNeeded"
            },
            {
                "InstanceId": "i-0471e04240EXAMPLE",
                "BaselineId": "pb-09ca3fb51fEXAMPLE",
                "SnapshotId": "05d8ffb0-1bbe-4812-ba2d-d9b7bEXAMPLE",
                "PatchGroup": "Production",
                "OwnerInformation": "",
                "FailedCount": 0,
                "InstalledCount": 22,
                "InstalledOtherCount": 452,
                "InstalledPendingRebootCount": 4,
                "InstalledRejectedCount": 1,
                "MissingCount": 16,
                "UnreportedNotApplicableCount": 0,
                "NotApplicableCount": 401,
                "Operation": "Scan",
                "OperationEndTime": 1520964020,
                "OperationStartTime": 1520964019,
                "RebootOption": "RebootIfNeeded"
            }
        ]
    }

For more information, see `About Patch Compliance States <https://docs.aws.amazon.com/systems-manager/latest/userguide/about-patch-compliance-states.html>`__ in the *AWS Systems Manager User Guide*.