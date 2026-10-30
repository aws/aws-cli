**To start a DB cluster**

The following ``start-db-cluster`` example starts a DB cluster and its DB instances. ::

    aws rds start-db-cluster \
        --db-cluster-identifier mydbcluster

Output::

    {
        "DBCluster": {
            "AllocatedStorage": 1,
            "AvailabilityZones": [
                "us-west-2a",
                "us-west-2d",
                "us-west-2b"
            ],
            "BackupRetentionPeriod": 1,
            "DatabaseName": "mydb",
            "DBClusterIdentifier": "mydbcluster"
        }
    }

For more information, see `Stopping and starting an Amazon Aurora DB cluster <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-cluster-stop-start.html>`__ in the *Amazon Aurora User Guide*.