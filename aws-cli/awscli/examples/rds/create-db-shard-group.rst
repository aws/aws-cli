**To create a DB shard group**

The following ``create-db-shard-group`` example creates a DB shard group in an Aurora PostgreSQL primary DB cluster that's compatible with Aurora Serverless v2 and Aurora Limitless Database. Before you create the DB shard group, create the DB cluster with the ``create-db-cluster`` command and its writer DB instance with the ``create-db-instance`` command. ::

    aws rds create-db-shard-group \
        --db-shard-group-identifier my-db-shard-group \
        --db-cluster-identifier my-sv2-cluster \
        --max-acu 768

Output::

    {
        "DBShardGroupResourceId": "shardgroup-a6e3a0226aa243e2ac6c7a1234567890",
        "DBShardGroupIdentifier": "my-db-shard-group",
        "DBClusterIdentifier": "my-sv2-cluster",
        "MaxACU": 768.0,
        "ComputeRedundancy": 0,
        "Status": "creating",
        "PubliclyAccessible": false,
        "Endpoint": "my-sv2-cluster.limitless-cekycexample.us-west-2.rds.amazonaws.com"
    }

For more information, see `Using Aurora Serverless v2 <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html>`__ in the *Amazon Aurora User Guide*.
