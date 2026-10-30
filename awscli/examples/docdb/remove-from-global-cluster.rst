**To remove a cluster from a global DB cluster**

The following ``remove-from-global-cluster`` example detaches the specified cluster in the us-east-1 Region from an Amazon DocumentDB global DB cluster. The cluster becomes a standalone cluster. In this example, it was the last remaining member, so ``GlobalClusterMembers`` is empty. ::

    aws docdb remove-from-global-cluster \
        --region us-east-1 \
        --global-cluster-identifier docdb-global-cluster \
        --db-cluster-identifier arn:aws:rds:us-east-1:123456789012:cluster:docdb-secondary-cluster

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
            "GlobalClusterMembers": [],
            "TagList": []
        }
    }

For more information, see `Removing a cluster from an Amazon DocumentDB global cluster <https://docs.aws.amazon.com/documentdb/latest/devguide/global-clusters.manage.html#global-clusters.remove>`__ in the *Amazon DocumentDB Developer Guide*.
