**To reboot a DB shard group**

The following ``reboot-db-shard-group`` example reboots a DB shard group. To follow the progress of the reboot, use the ``describe-db-shard-groups`` command. ::

    aws rds reboot-db-shard-group \
        --db-shard-group-identifier my-db-shard-group

Output::

    {
        "DBShardGroupResourceId": "shardgroup-a6e3a0226aa243e2ac6c7a1234567890",
        "DBShardGroupIdentifier": "my-db-shard-group",
        "DBClusterIdentifier": "my-sv2-cluster",
        "MaxACU": 1000.0,
        "ComputeRedundancy": 0,
        "Status": "available",
        "PubliclyAccessible": false,
        "Endpoint": "my-sv2-cluster.limitless-cekycexample.us-west-2.rds.amazonaws.com"
    }

For more information, see `Rebooting an Amazon Aurora DB cluster or Amazon Aurora DB instance <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_RebootCluster.html>`__ in the *Amazon Aurora User Guide*.
