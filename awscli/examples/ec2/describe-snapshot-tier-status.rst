**Example 1: To view archived and standard tier snapshots**

The following ``describe-snapshot-tier-status`` example displays the archived and standard tier snapshots. ::

    aws ec2 describe-snapshots \
        --snapshot-ids snap-01234567890abcedf

Output::

    {
        "Snapshots": [
            {
                "Description": "Snap A",
                "Encrypted": false,
                "VolumeId": "vol-01234567890aaaaaa",
                "State": "completed",
                "VolumeSize": 8,
                "StartTime": "2021-09-07T21:00:00.000Z",
                "Progress": "100%",
                "OwnerId": "123456789012",
                "SnapshotId": "snap-01234567890aaaaaa",
                "StorageTier": "archive",
                "Tags": []
            },
            {
                "Description": "Snap B",
                "Encrypted": false,
                "VolumeId": "vol-09876543210bbbbbb",
                "State": "completed",
                "VolumeSize": 10,
                "StartTime": "2021-09-14T21:00:00.000Z",
                "Progress": "100%",
                "OwnerId": "123456789012",
                "SnapshotId": "snap-09876543210bbbbbb",
                "StorageTier": "standard",           
                "RestoreExpiryTime": "2019-09-19T21:00:00.000Z",
                "Tags": []
            },
            {
                "Description": "Snap C",
                "Encrypted": false,
                "VolumeId": "vol-054321543210cccccc",
                "State": "completed",
                "VolumeSize": 12,
                "StartTime": "2021-08-01T21:00:00.000Z",
                "Progress": "100%",
                "OwnerId": "123456789012",
                "SnapshotId": "snap-054321543210cccccc",
                "StorageTier": "standard",
                "Tags": []
            }
        ]
    }

The ``StorageTier`` response parameter indicates whether the snapshot is currently archived. ``archive`` indicates that the snapshot is currently archived and stored in the archive tier, and ``standard`` indicates that the snapshot is currently not archived and that it is stored in the standard tier. In this example, only ``Snap A`` is archived. ``Snap B`` and ``Snap C`` are not archived.

Additionally, the ``RestoreExpiryTime`` response parameter is returned only for snapshots that are temporarily restored from the archive. It indicates when temporarily restored snapshots are to be automatically removed from the standard tier. It is not returned for snapshots that are permanently restored. 

In this example output, ``Snap C`` is temporarily restored, and it will be automatically removed from the standard tier at ``2021-09-19T21:00:00.000Z`` (September 19, 2021 at 21:00 UTC). 

For more information about snapshot archiving, see `Archive Amazon EBS snapshots <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snapshot-archive.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To view only snapshots that are stored in the archive tier**

The following ``describe-snapshot-tier-status`` example displays only snapshots that are stored in the archive tier. Include the ``--filter`` option for the filter name, specify ``storage-tier``, and for the filter value, specify ``archive``. ::

   aws ec2 describe-snapshots \
        --filters "Name=storage-tier,Values=archive"

Output::

    {
        "Snapshots": [
            {
                "Description": "Snap A",
                "Encrypted": false,
                "VolumeId": "vol-01234567890aaaaaa",
                "State": "completed",
                "VolumeSize": 8,
                "StartTime": "2021-09-07T21:00:00.000Z",
                "Progress": "100%",
                "OwnerId": "123456789012",
                "SnapshotId": "snap-01234567890aaaaaa",
                "StorageTier": "archive",
                "Tags": []
            },
        ]
    }

For more information about snapshot archiving, see `Archive Amazon EBS snapshots <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snapshot-archive.html>`__ in the *Amazon EC2 User Guide*.