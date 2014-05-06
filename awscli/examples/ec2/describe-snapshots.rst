**To describe a snapshot**

This example command describes a snapshot with the snapshot ID of ``snap-1234abcd``.

Command::

  aws ec2 describe-snapshots --snapshot-id snap-1234abcd

Output::

   {
       "Snapshots": [
           {
               "Description": "This is my snapshot.",
               "VolumeId": "vol-a1b2c3d4",
               "State": "completed",
               "VolumeSize": 8,
               "Progress": "100%",
               "StartTime": "2014-02-28T21:28:32.000Z",
               "SnapshotId": "snap-b2c3d4e5",
               "OwnerId": "012345678910"
           }
       ]
   }

**To describe snapshots using filters**

This example command describes all snapshots owned by the ID 012345678910 that are in the ``pending`` status.

Command::

  aws ec2 describe-snapshots --owner-ids 012345678910 --filters Name=status,Values=pending

Output::

   {
       "Snapshots": [
           {
               "Description": "This is my copied snapshot.",
               "VolumeId": "vol-4d3c2b1a",
               "State": "pending",
               "VolumeSize": 8,
               "Progress": "87%",
               "StartTime": "2014-02-28T21:37:27.000Z",
               "SnapshotId": "snap-d4e5f6g7",
               "OwnerId": "012345678910"
           }
       ]
   }
