**To get the patch summary states for instances**

The following ``describe-instance-patch-states`` example retrieves details about the patch summary states for the specified instance. ::

    aws ssm describe-instance-patch-states \
        --instance-ids "i-1234567890abcdef0"

Output::

    {
        "InstancePatchStates": [
            {
                "InstanceId": "i-1234567890abcdef0",
                "PatchGroup": "",
                "BaselineId": "pb-0713accee01234567",
                "SnapshotId": "521c3536-930c-4aa9-950e-01234567abcd",
                "OwnerInformation": "",
                "InstalledCount": 2,
                "InstalledOtherCount": 12,
                "InstalledRejectedCount": 0,
                "MissingCount": 1,
                "FailedCount": 0,
                "NotApplicableCount": 675,
                "OperationStartTime": 1548438382.462,
                "OperationEndTime": 1548438392.176,
                "Operation": "Scan"
            }
        ]
    }

For more information, see `About Patch Compliance <https://docs.aws.amazon.com/systems-manager/latest/userguide/about-patch-compliance.html>`__ in the *AWS Systems Manager User Guide*.
