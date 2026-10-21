**To reboot a Multi-AZ DB cluster**

The following ``reboot-db-cluster`` example reboots all the DB instances in the specified Multi-AZ DB cluster. Use this operation only for a non-Aurora Multi-AZ DB cluster. ::

    aws rds reboot-db-cluster \
        --db-cluster-identifier test-pg-multiaz-cluster

Output::

    {
        "DBCluster": {
            "AllocatedStorage": 20,
            "AvailabilityZones": [
                "us-east-1b",
                "us-east-1c",
                "us-east-1f"
            ],
            "BackupRetentionPeriod": 7,
            "DBClusterIdentifier": "test-pg-multiaz-cluster",
            "DBClusterParameterGroup": "default.postgres17",
            "DBSubnetGroup": "default",
            "Status": "available",
            "Endpoint": "test-pg-multiaz-cluster.cluster-cnpexample.us-east-1.rds.amazonaws.com",
            "ReaderEndpoint": "test-pg-multiaz-cluster.cluster-ro-cnpexample.us-east-1.rds.amazonaws.com",
            "MultiAZ": true,
            "Engine": "postgres",
            "EngineVersion": "17.5",
            ...some output truncated...
        }
    }

For more information, see `Rebooting a Multi-AZ DB cluster and reader DB instances for Amazon RDS <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts-rebooting.html>`__ in the *Amazon RDS User Guide*.
