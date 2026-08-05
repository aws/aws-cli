**To restore snapshots from the Recycle Bin**

The following ``restore-snapshot-from-recycle-bin`` example restores a snapshot from the Recycle Bin. When you restore a snapshot from the Recycle Bin, the snapshot is immediately available for use, and it is removed from the Recycle Bin. You can use a restored snapshot in the same way that you use any other snapshot in your account. ::

    aws ec2 restore-snapshot-from-recycle-bin \
        --snapshot-id snap-01234567890abcdef

Output::

    {
        "SnapshotId": "snap-01234567890abcdef",
        "Description": "Monthly data backup snapshot",
        "Encrypted": false,
        "OwnerId": "111122223333",
        "Progress": "99%",
        "StartTime": "2021-12-01T13:00:00.000000+00:00",
        "State": "recovering",
        "VolumeId": "vol-ffffffff",
        "VolumeSize": 30
    }

For more information about Recycle Bin, see `Recover deleted snapshots from the Recycle Bin <https://docs.aws.amazon.com/ebs/latest/userguide/recycle-bin-working-with-snaps.html>`__ in the *Amazon EBS User Guide*.
