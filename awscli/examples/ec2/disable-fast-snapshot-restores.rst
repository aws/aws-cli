**To disable fast snapshot restore**

The following ``disable-fast-snapshot-restores`` example disables fast snapshot restore for the specified snapshot in the specified Availability Zone. ::

    aws ec2 disable-fast-snapshot-restores \
        --availability-zones us-west-2a \
        --source-snapshot-ids snap-1234567890abcdef0

Output::

    {
        "Successful": [
            {
                "SnapshotId": "snap-1234567890abcdef0",
                "AvailabilityZone": "us-west-2a",
                "State": "disabling",
                "StateTransitionReason": "Client.UserInitiated",
                "OwnerId": "123456789012",
                "EnablingTime": "2020-01-25T23:57:49.602Z"
            }
        ],
        "Unsuccessful": []
    }

For more information, see `Amazon EBS fast snapshot restore <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-fast-snapshot-restore.html>`__ in the *Amazon EBS User Guide*.
