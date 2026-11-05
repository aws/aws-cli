**To delete an automated backup of a DB cluster**

The following ``delete-db-cluster-automated-backup`` example deletes the automated backup for the specified DB cluster resource ID. To find the resource ID, use the ``describe-db-cluster-automated-backups`` command. ::

    aws rds delete-db-cluster-automated-backup \
        --db-cluster-resource-id cluster-ABCD1234EFGH5678IJKL90MNOP

Output::

    {
        "DBClusterAutomatedBackup": {
            "Engine": "aurora-postgresql",
            "DBClusterAutomatedBackupsArn": "arn:aws:rds:us-west-2:123456789012:cluster-auto-backup:cab-abcd1234efgh5678ijkl90mnopqrst5678uvwx1234yzab56cdef7890abcd1234",
            "DBClusterIdentifier": "test-aurora-cluster",
            "RestoreWindow": {},
            "MasterUsername": "postgres",
            "DbClusterResourceId": "cluster-ABCD1234EFGH5678IJKL90MNOP",
            "Region": "us-west-2",
            "Status": "deleted",
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
    }

For more information, see `Deleting retained automated backups for Amazon Aurora <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Backups.Retaining.Deleting.html>`__ in the *Amazon Aurora User Guide*.
