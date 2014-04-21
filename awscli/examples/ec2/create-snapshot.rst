**To create a snapshot**

This example command creates a snapshot of the volume with a volume ID of ``vol-1234abcd`` and a short description to identify the snapshot.

Command::

  aws ec2 create-snapshot --volume-id vol-1234abcd --description "This is my root volume snapshot."

Output::

   {
       "Description": "This is my root volume snapshot.",
       "Tags": [],
       "VolumeId": "vol-1234abcd",
       "State": "pending",
       "VolumeSize": 8,
       "StartTime": "2014-02-28T21:06:01.000Z",
       "OwnerId": "012345678910",
       "SnapshotId": "snap-1a2b3c4d"
   }