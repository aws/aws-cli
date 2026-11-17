**To restore a DB instance from a backup in Amazon S3**

The following ``restore-db-instance-from-s3`` example creates a new DB instance named ``restored-test-instance`` from an existing backup in the ``my-backups`` S3 bucket. ::

    aws rds restore-db-instance-from-s3 \
        --db-instance-identifier restored-test-instance \
        --allocated-storage 250 \
        --db-instance-class db.m4.large \
        --engine mysql \
        --master-username master \
        --master-user-password secret99 \
        --s3-bucket-name my-backups \
        --s3-ingestion-role-arn arn:aws:iam::123456789012:role/my-role \
        --source-engine mysql \
        --source-engine-version 5.6.27

Output::

    {
        "DBInstance": {
            "DBInstanceIdentifier": "restored-test-instance",
            "DBInstanceClass": "db.m4.large",
            "Engine": "mysql",
            "DBInstanceStatus": "creating",
            "MasterUsername": "master",
            "AllocatedStorage": 250,
            "PreferredBackupWindow": "08:20-08:50",
            "BackupRetentionPeriod": 1,
            "DBSecurityGroups": [],
            "VpcSecurityGroups": [
                {
                    "VpcSecurityGroupId": "sg-0123456789abcdef0",
                    "Status": "active"
                }
            ],
            "DBParameterGroups": [
                {
                    "DBParameterGroupName": "default.mysql5.6",
                    "ParameterApplyStatus": "in-sync"
                }
            ],
            "PreferredMaintenanceWindow": "tue:10:16-tue:10:46",
            "PendingModifiedValues": {
                "MasterUserPassword": "****"
            },
            "MultiAZ": false,
            "AutoMinorVersionUpgrade": true,
            "ReadReplicaDBInstanceIdentifiers": [],
            "LicenseModel": "general-public-license",
            "OptionGroupMemberships": [
                {
                    "OptionGroupName": "default:mysql-5-6",
                    "Status": "in-sync"
                }
            ],
            "PubliclyAccessible": false,
            "StorageType": "gp2",
            "StorageEncrypted": false,
            "DbiResourceId": "db-ABCDEFGHIJKLMNOPQRSTUEXAMPLE",
            "CACertificateIdentifier": "rds-ca-rsa2048-g1",
            "DomainMemberships": [],
            "CopyTagsToSnapshot": false,
            "MonitoringInterval": 0,
            "DBInstanceArn": "arn:aws:rds:us-west-2:123456789012:db:restored-test-instance",
            "IAMDatabaseAuthenticationEnabled": false,
            "PerformanceInsightsEnabled": false,
            "DeletionProtection": false,
            "AssociatedRoles": [],
            "TagList": []
        }
    }

For more information, see `Restoring a backup into an Amazon RDS for MySQL DB instance <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/MySQL.Procedural.Importing.html>`__ in the *Amazon RDS User Guide*.

For more information, see `Restoring a backup into an Amazon RDS for MySQL DB instance <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/MySQL.Procedural.Importing.html>`__ in the *Amazon RDS User Guide*.
