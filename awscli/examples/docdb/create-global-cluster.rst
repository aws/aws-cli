**To create a global DB cluster**

The following ``create-global-cluster`` example creates an Amazon DocumentDB global DB cluster that uses the specified cluster as its primary cluster. ::

    aws docdb create-global-cluster \
        --global-cluster-identifier docdb-global-cluster \
        --source-db-cluster-identifier arn:aws:rds:us-west-2:123456789012:cluster:docdb-primary-cluster

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
            "DeletionProtection": false,
            "GlobalClusterMembers": [
                {
                    "DBClusterArn": "arn:aws:rds:us-west-2:123456789012:cluster:docdb-primary-cluster",
                    "Readers": [],
                    "IsWriter": true,
                    "SynchronizationStatus": "connected"
                }
            ],
            "TagList": []
        }
    }

For more information, see `Creating an Amazon DocumentDB global cluster <https://docs.aws.amazon.com/documentdb/latest/devguide/global-clusters.get-started.html#global-clusters-create>`__ in the *Amazon DocumentDB Developer Guide*.
