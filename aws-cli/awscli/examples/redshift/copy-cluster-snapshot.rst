**To copy a cluster snapshot**

The following ``copy-cluster-snapshot`` example creates a copy of the automated snapshot ``cm:examplecluster-2013-01-22-19-27-58`` named ``my-saved-snapshot-copy``.  By default, the output is in JSON format. ::

    aws redshift copy-cluster-snapshot \
        --source-snapshot-identifier cm:examplecluster-2013-01-22-19-27-58 \
        --target-snapshot-identifier my-saved-snapshot-copy

Output::

    {
        "Snapshot": {
            "Status": "available",
            "SnapshotCreateTime": "2013-01-22T19:27:58.931Z",
            "AvailabilityZone": "us-west-2c",
            "ClusterVersion": "1.0",
            "MasterUsername": "adminuser",
            "DBName": "dev",
            "ClusterCreateTime": "2013-01-22T19:23:59.368Z",
            "SnapshotType": "manual",
            "NodeType": "dw.hs1.xlarge",
            "ClusterIdentifier": "examplecluster",
            "Port": 5439,
            "NumberOfNodes": 2,
            "SnapshotIdentifier": "my-saved-snapshot-copy"
        }
    }

For more information, see `Copying an automated snapshot <https://docs.aws.amazon.com/redshift/latest/mgmt/snapshot-copy.html>`__ in the *Amazon Redshift Management Guide*.
