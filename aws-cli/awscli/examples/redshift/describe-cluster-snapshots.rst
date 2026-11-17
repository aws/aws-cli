**To get a description of all cluster snapshots**

The following ``describe-cluster-snapshots`` example returns a description of all cluster snapshots for the
account.  By default, the output is in JSON format. ::

    aws redshift describe-cluster-snapshots

Output::

    {
        "Snapshots": [
            {
                "Status": "available",
                "SnapshotCreateTime": "2013-07-17T22:02:22.852Z",
                "EstimatedSecondsToCompletion": -1,
                "AvailabilityZone": "us-west-2a",
                "ClusterVersion": "1.0",
                "MasterUsername": "adminuser",
                "Encrypted": false,
                "OwnerAccount": "123456789012",
                "BackupProgressInMegaBytes": 20.0,
                "ElapsedTimeInSeconds": 0,
                "DBName": "dev",
                "CurrentBackupRateInMegaBytesPerSecond": 0.0,
                "ClusterCreateTime": "2013-01-22T21:59:29.559Z",
                "ActualIncrementalBackupSizeInMegaBytes": 20.0,
                "SnapshotType": "automated",
                "NodeType": "dw.hs1.xlarge",
                "ClusterIdentifier": "mycluster",
                "Port": 5439,
                "TotalBackupSizeInMegaBytes": 20.0,
                "NumberOfNodes": 2,
                "SnapshotIdentifier": "cm:mycluster-2013-01-22-22-04-18"
            },
            {
                "EstimatedSecondsToCompletion": 0,
                "OwnerAccount": "123456789012",
                "CurrentBackupRateInMegaBytesPerSecond": 0.1534,
                "ActualIncrementalBackupSizeInMegaBytes": 11.0,
                "NumberOfNodes": 2,
                "Status": "available",
                "ClusterVersion": "1.0",
                "MasterUsername": "adminuser",
                "AccountsWithRestoreAccess": [
                    {
                        "AccountId": "123456789111"
                } ],
                "TotalBackupSizeInMegaBytes": 20.0,
                "DBName": "dev",
                "BackupProgressInMegaBytes": 11.0,
                "ClusterCreateTime": "2013-01-22T21:59:29.559Z",
                "ElapsedTimeInSeconds": 0,
                "ClusterIdentifier": "mycluster",
                "SnapshotCreateTime": "2013-07-17T22:04:18.947Z",
                "AvailabilityZone": "us-west-2a",
                "NodeType": "dw.hs1.xlarge",
                "Encrypted": false,
                "SnapshotType": "manual",
                "Port": 5439,
                "SnapshotIdentifier": "my-snapshot-id"
        } ]
    }

For more information, see `Amazon Redshift snapshots and backups <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-snapshots.html>`__ in the *Amazon Redshift Management Guide*.
