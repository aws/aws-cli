**To modify a DB shard group**

The following ``modify-db-shard-group`` example changes the maximum capacity of a DB shard group to 1000 Aurora capacity units (ACUs). To see the new maximum capacity after the change is applied, use the ``describe-db-shard-groups`` command. ::

    aws rds modify-db-shard-group \
        --db-shard-group-identifier my-db-shard-group \
        --max-acu 1000

Output::

    {
        "DBShardGroupResourceId": "shardgroup-a6e3a0226aa243e2ac6c7a1234567890",
        "DBShardGroupIdentifier": "my-db-shard-group",
        "DBClusterIdentifier": "my-sv2-cluster",
        "MaxACU": 768.0,
        "ComputeRedundancy": 0,
        "Status": "available",
        "PubliclyAccessible": false,
        "Endpoint": "my-sv2-cluster.limitless-cekycexample.us-west-2.rds.amazonaws.com"
    }

For more information, see `Amazon Aurora DB Clusters <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.html>`__ in the *Amazon Aurora User Guide*.
