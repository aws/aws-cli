**To copy a cluster snapshot**

The following ``copy-cluster-snapshot`` example creates a copy of the automated snapshot ``cm:examplecluster-2013-01-22-19-27-58`` named ``my-saved-snapshot-copy``.  By default, the output is in JSON format. ::

    aws redshift copy-cluster-snapshot \
        --source-snapshot-identifier cm:examplecluster-2013-01-22-19-27-58 \
        --target-snapshot-identifier my-saved-snapshot-copy

Result::

    {
        "Snapshot": {
            "Status": "available",
            "SnapshotCreateTime": "2013-01-22T19:27:58.931Z",
            "AvailabilityZone": "us-east-1c",
            "ClusterVersion": "1.0",
            "MasterUsername": "adminuser",
            "DBName": "dev",
            "ClusterCreateTime": "2013-01-22T19:23:59.368Z",
            "SnapshotType": "manual",
            "NodeType": "dw.hs1.xlarge",
            "ClusterIdentifier": "examplecluster",
            "Port": 5439,
            "NumberOfNodes": "2",
            "SnapshotIdentifier": "my-saved-snapshot-copy"
        },
        "ResponseMetadata": {
            "RequestId": "3b279691-64e3-11e2-bec0-17624ad140dd"
        }
    }


