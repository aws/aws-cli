**To describe the automated backups of a DB cluster**

The following ``describe-db-cluster-automated-backups`` example retrieves the automated backup for the specified DB cluster, including the window of time that you can restore to. ::

    aws rds describe-db-cluster-automated-backups \
        --db-cluster-identifier test-aurora-cluster

Output::

    {
        "DBClusterAutomatedBackups": [
            {
                "Engine": "aurora-postgresql",
                "DBClusterAutomatedBackupsArn": "arn:aws:rds:us-west-2:123456789012:cluster-auto-backup:cab-abcd1234efgh5678ijkl90mnopqrst5678uvwx1234yzab56cdef7890abcd1234",
                "DBClusterIdentifier": "test-aurora-cluster",
                "RestoreWindow": {
                    "EarliestTime": "2026-09-12T11:38:22.795000+00:00",
                    "LatestTime": "2026-09-12T11:47:16.053000+00:00"
                },
                "MasterUsername": "postgres",
                "DbClusterResourceId": "cluster-ABCD1234EFGH5678IJKL90MNOP",
                "Region": "us-west-2",
                "Status": "active",
                "IAMDatabaseAuthenticationEnabled": false,
                "ClusterCreateTime": "2026-09-12T11:38:04+00:00",
                "StorageEncrypted": true,
                "StorageEncryptionType": "sse-kms",
                "AllocatedStorage": 1,
                "EngineVersion": "17.7",
                "DBClusterArn": "arn:aws:rds:us-west-2:123456789012:cluster:test-aurora-cluster",
                "BackupRetentionPeriod": 7,
                "PreferredBackupWindow": "04:30-05:00",
                "EngineMode": "provisioned",
                "AvailabilityZones": [
                    "us-west-2b",
                    "us-west-2d",
                    "us-west-2c"
                ],
                "Port": 5432,
                "KmsKeyId": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "TagList": []
            }
        ]
    }

For more information, see `Viewing retained automated backups for Amazon Aurora <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Backups.Retaining.Viewing.html>`__ in the *Amazon Aurora User Guide*.
