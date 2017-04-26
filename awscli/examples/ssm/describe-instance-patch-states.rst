**To get the patch summary states for instances**

This example gets the patch summary states for an instance.

Command::

  aws ssm describe-instance-patch-states --instance-ids "i-08ee91c0b17045407" "i-09a618aec652973a9"

Output::

  {
    "InstancePatchStates": [
      {
		"OperationStartTime":"2016-12-09T05:00:00Z",
		"FailedCount":0,
		"InstanceId":"i-08ee91c0b17045407",
		"OwnerInformation":"",
		"NotApplicableCount":2077,
		"OperationEndTime":"2016-12-09T05:02:37Z",
		"PatchGroup":"Production",
		"InstalledOtherCount":186,
		"MissingCount":7,
		"SnapshotId":"b0e65479-79be-4288-9f88-81c96bc3ed5e",
		"Operation":"Scan",
		"InstalledCount":72
	  },
	  {
		"OperationStartTime":"2016-12-09T04:59:09Z",
		"FailedCount":0,
		"InstanceId":"i-09a618aec652973a9"
		"OwnerInformation":"",
		"NotApplicableCount":1637,
		"OperationEndTime":"2016-12-09T05:03:57Z",
		"PatchGroup":"Production",
		"InstalledOtherCount":388,
		"MissingCount":2,
		"SnapshotId":"b0e65479-79be-4288-9f88-81c96bc3ed5e",
		"Operation":"Scan",
		"InstalledCount":141
	  }
	]
  }
