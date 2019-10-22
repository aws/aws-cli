**Example 1: To describe a snapshot**

The following ``describe-snapshots`` example describes the specified snapshot. ::

    aws ec2 describe-snapshots \
        --snapshot-id snap-1234567890abcdef0

Output::

    {
        "Snapshots": [
            {
                "Description": "This is my snapshot",
                "Encrypted": false,
                "VolumeId": "vol-049df61146c4d7901",
                "State": "completed",
                "VolumeSize": 8,
                "StartTime": "2014-02-28T21:28:32.000Z",
                "Progress": "100%",
                "OwnerId": "012345678910",
                "SnapshotId": "snap-1234567890abcdef0"
            }
        ]
    }

**Example 2: To describe snapshots using filters**

The following ``describe-snapshots`` example describes all snapshots owned by the specified AWS account that are in the ``pending`` state. ::

    aws ec2 describe-snapshots \
        --owner-ids 012345678910 \
        --filters Name=status,Values=pending

Output::

    {
        "Snapshots": [
            {
                "Description": "This is my copied snapshot",
                "Encrypted": true,
                "VolumeId": "vol-1234567890abcdef0",
                "State": "pending",
                "VolumeSize": 8,
                "StartTime": "2014-02-28T21:37:27.000Z",
                "Progress": "87%",
                "OwnerId": "012345678910",
                "SnapshotId": "snap-066877671789bd71b"
            }
        ]
    }

**Example 3: To describe tagged snapshots and filter the output**

The following ``describe-snapshots`` example describes all snapshots that have the tag ``Group=Prod``. The output is filtered to display only the snapshot IDs and the time the snapshot was started. ::

    aws ec2 describe-snapshots \
        --filters Name=tag:Group,Values=Prod \
        --query "Snapshots[*].{ID:SnapshotId,Time:StartTime}"

Output::

    [
        {
            "ID": "snap-1234567890abcdef0", 
            "Time": "2014-08-04T12:48:18.000Z"
        }
    ]
