**To delete a global DB cluster**

The following ``delete-global-cluster`` example deletes an Amazon DocumentDB global DB cluster. Before you delete a global DB cluster, you must remove all of its member clusters and turn off deletion protection. The output shows the cluster that you're deleting, but subsequent ``describe-global-clusters`` commands don't list that DB cluster. ::

    aws docdb delete-global-cluster \
        --global-cluster-identifier docdb-global-cluster

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
            "GlobalClusterMembers": [],
            "TagList": []
        }
    }

For more information, see `Deleting a cluster from an Amazon DocumentDB global cluster <https://docs.aws.amazon.com/documentdb/latest/devguide/global-clusters.manage.html#global-clusters.delete>`__ in the *Amazon DocumentDB Developer Guide*.
