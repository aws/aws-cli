**To enable fast snapshot restore**

The following ``enable-fast-snapshot-restores`` example enables fast snapshot restore for the specified snapshot in the specified Availability Zones. ::

    aws ec2 enable-fast-snapshot-restores \
        --availability-zones us-west-2a us-west-2b \
        --source-snapshot-ids snap-1234567890abcdef0

Output::

    {
        "Successful": [
            {
                "SnapshotId": "snap-1234567890abcdef0",
                "AvailabilityZone": "us-west-2a",
                "State": "enabling",
                "StateTransitionReason": "Client.UserInitiated",
                "OwnerId": "123456789012",
                "EnablingTime": "2020-01-25T23:57:49.602Z"
            },
            {
                "SnapshotId": "snap-1234567890abcdef0",
                "AvailabilityZone": "us-west-2b",
                "State": "enabling",
                "StateTransitionReason": "Client.UserInitiated",
                "OwnerId": "123456789012",
                "EnablingTime": "2020-01-25T23:57:49.596Z"
            }
        ],
        "Unsuccessful": []
    }

For more information, see `Amazon EBS fast snapshot restore <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-fast-snapshot-restore.html>`__ in the *Amazon EBS User Guide*.
