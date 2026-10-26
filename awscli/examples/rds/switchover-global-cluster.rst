**To switch over a global database**

The following ``switchover-global-cluster`` example promotes the specified secondary cluster to be the primary cluster of the global database. Run this command in the Region that hosts the current primary cluster. ::

    aws rds switchover-global-cluster \
        --region us-east-1 \
        --global-cluster-identifier global-database \
        --target-db-cluster-identifier arn:aws:rds:us-east-2:123456789012:cluster:secondary-cluster

Output::

    {
        "GlobalCluster": {
            "GlobalClusterIdentifier": "global-database",
            "GlobalClusterResourceId": "cluster-f0e523bfe07aabb",
            "GlobalClusterArn": "arn:aws:rds::123456789012:global-cluster:global-database",
            "Status": "switching-over",
            "Engine": "aurora-postgresql",
            "EngineVersion": "17.7",
            "EngineLifecycleSupport": "open-source-rds-extended-support-disabled",
            "StorageEncrypted": true,
            "StorageEncryptionType": "sse-kms",
            "DeletionProtection": false,
            "GlobalClusterMembers": [
                {
                    "DBClusterArn": "arn:aws:rds:us-east-1:123456789012:cluster:primary-cluster",
                    "Readers": [
                        "arn:aws:rds:us-east-2:123456789012:cluster:secondary-cluster"
                    ],
                    "IsWriter": true,
                    "SynchronizationStatus": "connected"
                },
                {
                    "DBClusterArn": "arn:aws:rds:us-east-2:123456789012:cluster:secondary-cluster",
                    "Readers": [],
                    "IsWriter": false,
                    "GlobalWriteForwardingStatus": "disabled",
                    "SynchronizationStatus": "connected"
                }
            ],
            "Endpoint": "global-database.global-cnpexample.global.rds.amazonaws.com",
            "FailoverState": {
                "Status": "pending",
                "FromDbClusterArn": "arn:aws:rds:us-east-1:123456789012:cluster:primary-cluster",
                "ToDbClusterArn": "arn:aws:rds:us-east-2:123456789012:cluster:secondary-cluster",
                "IsDataLossAllowed": false
            },
            "TagList": []
        }
    }

For more information, see `Using switchover or failover in Amazon Aurora Global Database <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html>`__ in the *Amazon Aurora User Guide*.
