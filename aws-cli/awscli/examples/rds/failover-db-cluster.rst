**To force a failover for a DB cluster**

The following ``failover-db-cluster`` example promotes the specified Aurora Replica to be the primary DB instance, or writer, of the DB cluster. ::

    aws rds failover-db-cluster \
        --db-cluster-identifier test-aurora-cluster-failover \
        --target-db-instance-identifier test-aurora-cluster-failover-instance-1-reader

Output::

    {
        "DBCluster": {
            "AllocatedStorage": 1,
            "AvailabilityZones": [
                "us-west-2d",
                "us-west-2c",
                "us-west-2a"
            ],
            "BackupRetentionPeriod": 7,
            "DBClusterIdentifier": "test-aurora-cluster-failover",
            "DBClusterParameterGroup": "default.aurora-postgresql17",
            "DBSubnetGroup": "default",
            "Status": "available",
            "Endpoint": "test-aurora-cluster-failover.cluster-cnpexample.us-west-2.rds.amazonaws.com",
            "ReaderEndpoint": "test-aurora-cluster-failover.cluster-ro-cnpexample.us-west-2.rds.amazonaws.com",
            "MultiAZ": true,
            "Engine": "aurora-postgresql",
            "EngineVersion": "17.7",
            "Port": 5432,
            "MasterUsername": "postgres"
        }
    }

For more information, see `Failing over an Amazon Aurora DB cluster <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-failover.html>`__ in the *Amazon Aurora User Guide*.
