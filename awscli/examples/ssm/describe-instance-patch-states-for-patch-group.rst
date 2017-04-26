**To get the instance states for a patch group**

This example gets the patch summary states per-instance for a patch group.

Command::

  aws ssm describe-instance-patch-states-for-patch-group --patch-group "Production"

Output::

  {
    "InstancePatchStates": [
	   {
         "OperationStartTime":1481259600.0,
         "FailedCount":0,
         "InstanceId":"i-08ee91c0b17045407",
         "OwnerInformation":"",
         "NotApplicableCount":2077,
         "OperationEndTime":1481259757.0,
         "PatchGroup":"Production",
         "InstalledOtherCount":186,
         "MissingCount":7,
         "SnapshotId":"b0e65479-79be-4288-9f88-81c96bc3ed5e",
         "Operation":"Scan",
         "InstalledCount":72
       },
       {
         "OperationStartTime":1481259602.0,
         "FailedCount":0,
         "InstanceId":"i-0fff3aab684d01b23",
         "OwnerInformation":"",
         "NotApplicableCount":2692,
         "OperationEndTime":1481259613.0,
         "PatchGroup":"Production",
         "InstalledOtherCount":3,
         "MissingCount":1,
         "SnapshotId":"b0e65479-79be-4288-9f88-81c96bc3ed5e",
         "Operation":"Scan",
         "InstalledCount":1
       },
	   ...
	]
  }
