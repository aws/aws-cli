**To modify a global DB cluster**

The following ``modify-global-cluster`` example enables deletion protection for an Amazon DocumentDB global DB cluster. ::

    aws docdb modify-global-cluster \
        --global-cluster-identifier docdb-global-cluster \
        --deletion-protection

Output::

    {
        "GlobalCluster": {
            "GlobalClusterIdentifier": "docdb-global-cluster",
            "GlobalClusterResourceId": "cluster-a1b2c3d4e5f6a7b8",
            "GlobalClusterArn": "arn:aws:rds::123456789012:global-cluster:docdb-global-cluster",
            "Status": "available",
            "Engine": "docdb",
            "EngineVersion": "8.0.0",
            "StorageEncrypted": true,
            "DeletionProtection": true,
            "GlobalClusterMembers": [
                {
                    "DBClusterArn": "arn:aws:rds:us-west-2:123456789012:cluster:docdb-primary-cluster",
                    "Readers": [
                        "arn:aws:rds:us-east-1:123456789012:cluster:docdb-secondary-cluster"
                    ],
                    "IsWriter": true,
                    "SynchronizationStatus": "connected"
                },
                {
                    "DBClusterArn": "arn:aws:rds:us-east-1:123456789012:cluster:docdb-secondary-cluster",
                    "Readers": [],
                    "IsWriter": false,
                    "SynchronizationStatus": "connected"
                }
            ],
            "TagList": []
        }
    }

For more information, see `Modifying an Amazon DocumentDB global cluster <https://docs.aws.amazon.com/documentdb/latest/devguide/global-clusters.manage.html#global-clusters.modify>`__ in the *Amazon DocumentDB Developer Guide*.
