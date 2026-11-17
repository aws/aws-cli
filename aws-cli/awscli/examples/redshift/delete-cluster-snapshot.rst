**To delete a cluster snapshot**

The following ``delete-cluster-snapshot`` example deletes a cluster snapshot. ::

    aws redshift delete-cluster-snapshot \
        --snapshot-identifier my-snapshot-id

Output::

    {
        "Snapshot": {
            "SnapshotIdentifier": "my-snapshot-id",
            "ClusterIdentifier": "mycluster",
            "SnapshotCreateTime": "2013-01-22T22:20:33.548Z",
            "Status": "deleted",
            "Port": 5439,
            "AvailabilityZone": "us-west-2a",
            "ClusterCreateTime": "2013-01-22T21:59:29.559Z",
            "MasterUsername": "adminuser",
            "ClusterVersion": "1.0",
            "SnapshotType": "manual",
            "NodeType": "dc2.large",
            "NumberOfNodes": 2,
            "DBName": "dev",
            "Encrypted": false,
            "EncryptedWithHSM": false,
            "OwnerAccount": "123456789012",
            "TotalBackupSizeInMegaBytes": 20.0,
            "ActualIncrementalBackupSizeInMegaBytes": 20.0,
            "BackupProgressInMegaBytes": 20.0,
            "CurrentBackupRateInMegaBytesPerSecond": 0.0,
            "EstimatedSecondsToCompletion": -1,
            "ElapsedTimeInSeconds": 0,
            "Tags": [],
            "EnhancedVpcRouting": false,
            "MaintenanceTrackName": "current",
            "ManualSnapshotRetentionPeriod": -1
        }
    }

For more information, see `Deleting a manual snapshot <https://docs.aws.amazon.com/redshift/latest/mgmt/snapshot-delete.html>`__ in the *Amazon Redshift Management Guide*.
