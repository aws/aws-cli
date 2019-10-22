**To get the patch summary states for instances**

This example gets the patch summary states for an instance.

Command::

  aws ssm describe-instance-patch-states --instance-ids "i-1234567890abcdef0"

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
