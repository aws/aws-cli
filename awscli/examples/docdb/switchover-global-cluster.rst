**To switch over a global DB cluster**

The following ``switchover-global-cluster`` example promotes the specified secondary cluster to be the primary cluster of the global DB cluster. ::

    aws docdb switchover-global-cluster \
        --global-cluster-identifier docdb-global-cluster \
        --target-db-cluster-identifier arn:aws:rds:us-east-1:123456789012:cluster:docdb-secondary-cluster

Output::

    {
        "GlobalCluster": {
            "GlobalClusterIdentifier": "docdb-global-cluster",
            "GlobalClusterResourceId": "cluster-a1b2c3d4e5f6a7b8",
            "GlobalClusterArn": "arn:aws:rds::123456789012:global-cluster:docdb-global-cluster",
            "Status": "switching-over",
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
            "FailoverState": {
                "Status": "pending",
                "FromDbClusterArn": "arn:aws:rds:us-west-2:123456789012:cluster:docdb-primary-cluster",
                "ToDbClusterArn": "arn:aws:rds:us-east-1:123456789012:cluster:docdb-secondary-cluster",
                "IsDataLossAllowed": false
            },
            "TagList": []
        }
    }

For more information, see `Performing a switchover for an Amazon DocumentDB global cluster <https://docs.aws.amazon.com/documentdb/latest/devguide/global-clusters-disaster-recovery.html#global-cluster-switchover>`__ in the *Amazon DocumentDB Developer Guide*.
