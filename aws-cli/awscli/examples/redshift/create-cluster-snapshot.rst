**To create a cluster snapshot**

The following ``create-cluster-snapshot`` example creates a new cluster snapshot.  By default, the output is in JSON format. ::

    aws redshift create-cluster-snapshot \
        --cluster-identifier mycluster \
        --snapshot-identifier my-snapshot-id

Output::

    {
        "Snapshot": {
            "Status": "creating",
            "SnapshotCreateTime": "2013-01-22T22:20:33.548Z",
            "AvailabilityZone": "us-west-2a",
            "ClusterVersion": "1.0",
            "MasterUsername": "adminuser",
            "DBName": "dev",
            "ClusterCreateTime": "2013-01-22T21:59:29.559Z",
            "SnapshotType": "manual",
            "NodeType": "dw.hs1.xlarge",
            "ClusterIdentifier": "mycluster",
            "Port": 5439,
            "NumberOfNodes": 2,
            "SnapshotIdentifier": "my-snapshot-id"
        }
    }

For more information, see `Creating a manual snapshot <https://docs.aws.amazon.com/redshift/latest/mgmt/snapshot-create.html>`__ in the *Amazon Redshift Management Guide*.
