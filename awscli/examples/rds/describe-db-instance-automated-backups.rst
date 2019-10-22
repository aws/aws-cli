**To describe the automated backups for a DB instance**

The following ``describe-db-instance-automated-backups`` example displays details about the automated backups for the specified DB instance. ::

    aws rds describe-db-instance-automated-backups \
        --db-instance-identifier database-mysql

Output::

    {
        "DBInstanceAutomatedBackups": [
            {
                "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:database-mysql",
                "DbiResourceId": "db-AKIAIOSFODNN7EXAMPLE",
                "Region": "us-east-1",
                "DBInstanceIdentifier": "database-mysql",
                "RestoreWindow": {
                    "EarliestTime": "2019-06-13T08:39:38.359Z",
                    "LatestTime": "2019-06-20T23:00:00Z"
                },
                "AllocatedStorage": 100,
                "Status": "active",
                "Port": 3306,
                "AvailabilityZone": "us-east-1b",
                "VpcId": "vpc-6594f31c",
                "InstanceCreateTime": "2019-04-30T15:45:53Z",
                "MasterUsername": "admin",
                "Engine": "mysql",
                "EngineVersion": "5.6.40",
                "LicenseModel": "general-public-license",
                "Iops": 1000,
                "OptionGroupName": "default:mysql-5-6",
                "Encrypted": true,
                "StorageType": "io1",
                "KmsKeyId": "arn:aws:kms:us-east-1:814387698303:key/AKIAIOSFODNN7EXAMPLE",
                "IAMDatabaseAuthenticationEnabled": false
            }
        ]
    }

For more information, see `Working With Backups <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html>`__ in the *Amazon RDS User Guide*.
