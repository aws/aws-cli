**To get the instance states for a patch group**

The following ``describe-instance-patch-states-for-patch-group`` example retrieves details about the patch summary states per-instance for the specified patch group. ::

    aws ssm describe-instance-patch-states-for-patch-group \
        --patch-group "Production"

Output::

    {
        "InstancePatchStates": [
            {
                "InstanceId": "i-1234567890abcdef0",
                "PatchGroup": "Production",
                "BaselineId": "pb-0713accee01234567",
                "SnapshotId": "521c3536-930c-4aa9-950e-01234567abcd",
                "OwnerInformation": "",
                "InstalledCount": 1,
                "InstalledOtherCount": 13,
                "InstalledRejectedCount": 0,
                "MissingCount": 3,
                "FailedCount": 0,
                "NotApplicableCount": 11,
                "OperationStartTime": 1550244665.723,
                "OperationEndTime": 1550244826.241,
                "Operation": "Scan"
            },
            {
                "InstanceId": "i-0987654321abcdef0",
                "PatchGroup": "Production",
                "BaselineId": "pb-0713accee01234567",
                "SnapshotId": "521c3536-930c-4aa9-950e-01234567abcd",
                "OwnerInformation": "",
                "InstalledCount": 1,
                "InstalledOtherCount": 7,
                "InstalledRejectedCount": 0,
                "MissingCount": 1,
                "FailedCount": 0,
                "NotApplicableCount": 13,
                "OperationStartTime": 1550245130.069,
                "OperationEndTime": 1550245143.043,
                "Operation": "Scan"
            }
        ]
    }

For more information, see `About Patch Compliance States <https://docs.aws.amazon.com/systems-manager/latest/userguide/about-patch-compliance-states.html>`__ in the *AWS Systems Manager User Guide*.
