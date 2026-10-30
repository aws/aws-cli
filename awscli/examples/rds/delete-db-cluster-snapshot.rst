**To delete a DB cluster snapshot**

The following ``delete-db-cluster-snapshot`` example deletes the specified DB cluster snapshot. ::

    aws rds delete-db-cluster-snapshot \
        --db-cluster-snapshot-identifier mydbclustersnapshot

Output::

    {
        "DBClusterSnapshot": {
            "AvailabilityZones": [
                "us-west-2a",
                "us-west-2b",
                "us-west-2d"
            ],
            "DBClusterSnapshotIdentifier": "mydbclustersnapshot",
            "DBClusterIdentifier": "mydbcluster",
            "SnapshotCreateTime": "2019-06-18T21:21:00.469Z",
            "Engine": "aurora-mysql",
            "AllocatedStorage": 0,
            "Status": "available",
            "Port": 0,
            "VpcId": "vpc-6594f31c",
            "ClusterCreateTime": "2019-04-15T14:18:42.785Z",
            "MasterUsername": "myadmin",
            "EngineVersion": "5.7.mysql_aurora.2.04.2",
            "LicenseModel": "aurora-mysql",
            "SnapshotType": "manual",
            "PercentProgress": 100,
            "StorageEncrypted": true,
            "KmsKeyId": "arn:aws:kms:us-west-2:123456789012:key/AKIAIOSFODNN7EXAMPLE",
            "DBClusterSnapshotArn": "arn:aws:rds:us-west-2:123456789012:cluster-snapshot:mydbclustersnapshot",
            "IAMDatabaseAuthenticationEnabled": false
        }
    }

For more information, see `Deleting a Snapshot <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_DeleteSnapshot.html>`__ in the *Amazon Aurora User Guide*.
