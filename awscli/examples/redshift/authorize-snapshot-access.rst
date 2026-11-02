**To authorize an AWS account to restore a snapshot**

The following ``authorize-snapshot-access`` example authorizes the AWS account ``123456789111`` to restore the snapshot ``my-snapshot-id``.
By default, the output is in JSON format. ::

    aws redshift authorize-snapshot-access \
        --snapshot-id my-snapshot-id \
        --account-with-restore-access 123456789111

Output::

    {
        "Snapshot": {
            "Status": "available",
            "SnapshotCreateTime": "2013-07-17T22:04:18.947Z",
            "EstimatedSecondsToCompletion": 0,
            "AvailabilityZone": "us-west-2a",
            "ClusterVersion": "1.0",
            "MasterUsername": "adminuser",
            "Encrypted": false,
            "OwnerAccount": "123456789012",
            "BackupProgressInMegaBytes": 11.0,
            "ElapsedTimeInSeconds": 0,
            "DBName": "dev",
            "CurrentBackupRateInMegaBytesPerSecond": 0.1534,
            "ClusterCreateTime": "2013-01-22T21:59:29.559Z",
            "ActualIncrementalBackupSizeInMegaBytes": 11.0,
            "SnapshotType": "manual",
            "NodeType": "dw.hs1.xlarge",
            "ClusterIdentifier": "mycluster",
            "TotalBackupSizeInMegaBytes": 20.0,
            "Port": 5439,
            "NumberOfNodes": 2,
            "SnapshotIdentifier": "my-snapshot-id"
        }
    }

For more information, see `Sharing a snapshot <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-snapshot-share-snapshot.html>`__ in the *Amazon Redshift Management Guide*.
