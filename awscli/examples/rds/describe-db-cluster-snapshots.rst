**To describe a DB cluster snapshot for a DB cluster**

The following ``describe-db-cluster-snapshots`` example retrieves the details for the DB cluster snapshots for the specified DB cluster. ::

    aws rds describe-db-cluster-snapshots \
        --db-cluster-identifier mydbcluster

Output::

    {
        "DBClusterSnapshots": [
            {
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2d"
                ],
                "DBClusterSnapshotIdentifier": "myclustersnapshotcopy",
                "DBClusterIdentifier": "mydbcluster",
                "SnapshotCreateTime": "2019-06-04T09:16:42.649Z",
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
                "DBClusterSnapshotArn": "arn:aws:rds:us-west-2:123456789012:cluster-snapshot:myclustersnapshotcopy",
                "IAMDatabaseAuthenticationEnabled": false
            },
            {
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2d"
                ],
                "DBClusterSnapshotIdentifier": "rds:mydbcluster-2019-06-20-09-16",
                "DBClusterIdentifier": "mydbcluster",
                "SnapshotCreateTime": "2019-06-20T09:16:26.569Z",
                "Engine": "aurora-mysql",
                "AllocatedStorage": 0,
                "Status": "available",
                "Port": 0,
                "VpcId": "vpc-6594f31c",
                "ClusterCreateTime": "2019-04-15T14:18:42.785Z",
                "MasterUsername": "myadmin",
                "EngineVersion": "5.7.mysql_aurora.2.04.2",
                "LicenseModel": "aurora-mysql",
                "SnapshotType": "automated",
                "PercentProgress": 100,
                "StorageEncrypted": true,
                "KmsKeyId": "arn:aws:kms:us-west-2:123456789012:key/AKIAIOSFODNN7EXAMPLE",
                "DBClusterSnapshotArn": "arn:aws:rds:us-west-2:123456789012:cluster-snapshot:rds:mydbcluster-2019-06-20-09-16",
                "IAMDatabaseAuthenticationEnabled": false
            }
        ]
    }

For more information, see `Creating a DB Cluster Snapshot <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_CreateSnapshotCluster.html>`__ in the *Amazon Aurora User Guide*.
