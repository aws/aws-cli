**To stop a cluster**

The following ``stop-cluster`` example stops an Amazon Aurora DB cluster. ::

    aws rds stop-db-cluster \
        --db-cluster-identifier mycluster

Output::

    {
        "DBCluster": {
            "AllocatedStorage": 1,
            "AvailabilityZones": [
                "us-east-1a",
                "us-east-1b",
                "us-east-1c"
            ],
            "BackupRetentionPeriod": 7,
            "DatabaseName": "",
            "DBClusterIdentifier": "mycluster",
            "DBClusterParameterGroup": "default.aurora-postgresql11",
            "DBSubnetGroup": "default",
            "Status": "available",
            "EarliestRestorableTime": "2020-07-01T06:17:10.807000+00:00",
            "Endpoint": "mycluster.cluster-cdgmuqiadpid.us-east-1.rds.amazonaws.com",
            "ReaderEndpoint": "mycluster.cluster-ro-cdgmuqiadpid.us-east-1.rds.amazonaws.com",
            "MultiAZ": true,
            "Engine": "aurora-postgresql",
            "EngineVersion": "11.6",
            "LatestRestorableTime": "2020-07-09T02:31:09.588000+00:00",
            "Port": 5432,
            "MasterUsername": "master",
            "PreferredBackupWindow": "06:11-06:41",
            "PreferredMaintenanceWindow": "mon:08:52-mon:09:22",
            "ReadReplicaIdentifiers": [],
            
            <remaining output omitted>            

        }
    }

For more information, see `Stopping and Starting an Amazon Aurora DB Cluster <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-cluster-stop-start.html>`__ in the *Amazon Aurora User Guide*.
