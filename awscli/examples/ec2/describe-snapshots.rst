**To describe a snapshot**

This example command describes a snapshot with the snapshot ID of ``snap-1234567890abcdef0``.

Command::

  aws ec2 describe-snapshots --snapshot-id snap-1234567890abcdef0

Output::

   {
       "Snapshots": [
           {
               "Description": "This is my snapshot.",
               "VolumeId": "vol-049df61146c4d7901",
               "State": "completed",
               "VolumeSize": 8,
               "Progress": "100%",
               "StartTime": "2014-02-28T21:28:32.000Z",
               "SnapshotId": "snap-1234567890abcdef0",
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
               "VolumeId": "vol-1234567890abcdef0",
               "State": "pending",
               "VolumeSize": 8,
               "Progress": "87%",
               "StartTime": "2014-02-28T21:37:27.000Z",
               "SnapshotId": "snap-066877671789bd71b",
               "OwnerId": "012345678910"
           }
       ]
   }

**To describe tagged snapshots and filter the output**

This example command describes all snapshots that have the tag ``Group=Prod``. The output is filtered to display only the snapshot IDs and the time the snapshot was started.

Command::

  aws ec2 describe-snapshots --filters Name=tag-key,Values="Group" Name=tag-value,Values="Prod" --query 'Snapshots[*].{ID:SnapshotId,Time:StartTime}'

Output::

   [
     {
        "ID": "snap-1234567890abcdef0", 
        "Time": "2014-08-04T12:48:18.000Z"
     }
   ]