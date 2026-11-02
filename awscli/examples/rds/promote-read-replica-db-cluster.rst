**To promote a DB cluster read replica**

The following ``promote-read-replica-db-cluster`` example promotes the specified read replica to become a standalone DB cluster. ::

    aws rds promote-read-replica-db-cluster \
        --db-cluster-identifier mydbcluster-1

Output::

    {
        "DBCluster": {
            "AllocatedStorage": 1,
            "AvailabilityZones": [
                "us-west-2a",
                "us-west-2b",
                "us-west-2c"
            ],
            "BackupRetentionPeriod": 1,
            "DatabaseName": "",
            "DBClusterIdentifier": "mydbcluster-1"
        }
    }

For more information, see `Promoting a read replica to be a DB cluster <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Replication.CrossRegion.Promote.html>`__ in the *Amazon Aurora User Guide*.