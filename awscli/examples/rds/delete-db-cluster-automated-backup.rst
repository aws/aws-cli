**To delete an automated backup of a DB cluster**

The following ``delete-db-cluster-automated-backup`` example deletes the automated backup for the specified DB cluster resource ID. To find the resource ID, use the ``describe-db-cluster-automated-backups`` command. ::

    aws rds delete-db-cluster-automated-backup \
        --db-cluster-resource-id cluster-ABCD1234EFGH5678IJKL90MNOP

Output::

    {
        "DBClusterAutomatedBackup": {
            "Engine": "aurora-postgresql",
            "DBClusterAutomatedBackupsArn": "arn:aws:rds:us-east-1:123456789012:cluster-auto-backup:cab-abcd1234efgh5678ijkl90mnopqrst5678uvwx1234yzab56cdef7890abcd1234",
            "DBClusterIdentifier": "test-aurora-cluster",
            "RestoreWindow": {},
            "MasterUsername": "postgres",
            "DbClusterResourceId": "cluster-ABCD1234EFGH5678IJKL90MNOP",
            "Region": "us-east-1",
            "Status": "deleted",
            "IAMDatabaseAuthenticationEnabled": false,
            "ClusterCreateTime": "2026-09-12T11:38:04+00:00",
            "StorageEncrypted": true,
            "StorageEncryptionType": "sse-kms",
            "AllocatedStorage": 1,
            "EngineVersion": "17.7",
            "DBClusterArn": "arn:aws:rds:us-east-1:123456789012:cluster:test-aurora-cluster",
            "BackupRetentionPeriod": 7,
            "PreferredBackupWindow": "04:30-05:00",
            "EngineMode": "provisioned",
            "AvailabilityZones": [
                "us-east-1b",
                "us-east-1d",
                "us-east-1c"
            ],
            "Port": 5432,
            "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab",
            "TagList": []
        }
    }

For more information, see `Deleting retained automated backups for Amazon Aurora <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Backups.Retaining.Deleting.html>`__ in the *Amazon Aurora User Guide*.
