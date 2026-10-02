**To describe recovery snapshots**

The following ``describe-recovery-snapshots`` example describes the recovery snapshots for the specified source server. ::

    aws drs describe-recovery-snapshots \
        --source-server-id s-1234567890abcdef0

Output::

    {
        "items": [
            {
                "ebsSnapshots": [
                    "snap-1234567890abcdef0"
                ],
                "expectedTimestamp": "2024-06-15T14:30:00.000Z",
                "recoverySnapshotVolumes": [
                    {
                        "volumeName": "/dev/xvda",
                        "volumeStorageSizeBytes": 32212254720
                    }
                ],
                "snapshotID": "pit-1234567890abcdef0",
                "sourceServerID": "s-1234567890abcdef0"
            }
        ]
    }

For more information, see `Performing a recovery <https://docs.aws.amazon.com/drs/latest/userguide/recovery.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
