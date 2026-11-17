**Example 1: To create a DB instance**

The following ``create-db-instance`` example uses the required options to launch a new DB instance. ::

    aws rds create-db-instance \
        --db-instance-identifier test-mysql-instance \
        --db-instance-class db.t3.micro \
        --engine mysql \
        --master-username admin \
        --master-user-password secret99 \
        --allocated-storage 20

Output::

    {
        "DBInstance": {
            "DBInstanceIdentifier": "test-mysql-instance",
            "DBInstanceClass": "db.t3.micro",
            "Engine": "mysql",
            "DBInstanceStatus": "creating",
            "MasterUsername": "admin",
            "AllocatedStorage": 20,
            "PreferredBackupWindow": "12:55-13:25",
            "BackupRetentionPeriod": 1,
            "DBSecurityGroups": [],
            "VpcSecurityGroups": [
                {
                    "VpcSecurityGroupId": "sg-12345abc",
                    "Status": "active"
                }
            ],
            "DBParameterGroups": [
                {
                    "DBParameterGroupName": "default.mysql5.7",
                    "ParameterApplyStatus": "in-sync"
                }
            ],
            "DBSubnetGroup": {
                "DBSubnetGroupName": "default",
                "DBSubnetGroupDescription": "default",
                "VpcId": "vpc-2ff2ff2f",
                "SubnetGroupStatus": "Complete",
                "Subnets": [
                    {
                        "SubnetIdentifier": "subnet-########",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2c"
                        },
                        "SubnetStatus": "Active"
                    },
                    {
                        "SubnetIdentifier": "subnet-########",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2d"
                        },
                        "SubnetStatus": "Active"
                    },
                    {
                        "SubnetIdentifier": "subnet-########",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2a"
                        },
                        "SubnetStatus": "Active"
                    },
                    {
                        "SubnetIdentifier": "subnet-########",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2b"
                        },
                        "SubnetStatus": "Active"
                    }
                ]
            },
            "PreferredMaintenanceWindow": "sun:08:07-sun:08:37",
            "PendingModifiedValues": {
                "MasterUserPassword": "****"
            },
            "MultiAZ": false,
            "EngineVersion": "5.7.22",
            "AutoMinorVersionUpgrade": true,
            "ReadReplicaDBInstanceIdentifiers": [],
            "LicenseModel": "general-public-license",
            "OptionGroupMemberships": [
                {
                    "OptionGroupName": "default:mysql-5-7",
                    "Status": "in-sync"
                }
            ],
            "PubliclyAccessible": true,
            "StorageType": "gp2",
            "DbInstancePort": 0,
            "StorageEncrypted": false,
            "DbiResourceId": "db-5555EXAMPLE44444444EXAMPLE",
            "CACertificateIdentifier": "rds-ca-2019",
            "DomainMemberships": [],
            "CopyTagsToSnapshot": false,
            "MonitoringInterval": 0,
            "DBInstanceArn": "arn:aws:rds:us-west-2:123456789012:db:test-mysql-instance",
            "IAMDatabaseAuthenticationEnabled": false,
            "PerformanceInsightsEnabled": false,
            "DeletionProtection": false,
            "AssociatedRoles": []
        }
    }

For more information, see `Creating an Amazon RDS DB Instance <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateDBInstance.html>`__ in the *Amazon RDS User Guide*.

**Example 2: To create an Aurora Serverless v2 writer DB instance in a DB cluster**

The following ``create-db-instance`` example creates an Aurora Serverless v2 primary (writer) DB instance in a DB cluster. When you use the console to create a DB cluster, Amazon RDS automatically creates the writer DB instance for your DB cluster. However, when you use the AWS CLI to create a DB cluster, you must explicitly create the writer DB instance for your DB cluster using the ``create-db-instance`` command. ::

    aws rds create-db-instance \
        --db-instance-identifier my-sv2-instance \
        --db-cluster-identifier my-sv2-cluster \
        --engine aurora-postgresql \
        --db-instance-class db.serverless

Output::

    {
        "DBInstance": {
            "DBInstanceIdentifier": "my-sv2-instance",
            "DBInstanceClass": "db.serverless",
            "Engine": "aurora-postgresql",
            "DBInstanceStatus": "creating",
            "MasterUsername": "myuser",
            "AllocatedStorage": 1,
            "PreferredBackupWindow": "06:05-06:35",
            "BackupRetentionPeriod": 1,
            "DBSecurityGroups": [],
            "VpcSecurityGroups": [
                {
                    "VpcSecurityGroupId": "sg-########",
                    "Status": "active"
                }
            ],
            "DBParameterGroups": [
                {
                    "DBParameterGroupName": "default.aurora-postgresql15",
                    "ParameterApplyStatus": "in-sync"
                }
            ],
            "DBSubnetGroup": {
                "DBSubnetGroupName": "default",
                "DBSubnetGroupDescription": "default",
                "VpcId": "vpc-########",
                "SubnetGroupStatus": "Complete",
                "Subnets": [
                    {
                        "SubnetIdentifier": "subnet-########",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2c"
                        },
                        "SubnetOutpost": {},
                        "SubnetStatus": "Active"
                    },
                    {
                        "SubnetIdentifier": "subnet-########",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2a"
                        },
                        "SubnetOutpost": {},
                        "SubnetStatus": "Active"
                    },
                    {
                        "SubnetIdentifier": "subnet-########",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2b"
                        },
                        "SubnetOutpost": {},
                        "SubnetStatus": "Active"
                    }
                ]
            },
            "PreferredMaintenanceWindow": "fri:09:01-fri:09:31",
            "PendingModifiedValues": {
                "PendingCloudwatchLogsExports": {
                    "LogTypesToEnable": [
                        "postgresql"
                    ]
                }
            },
            "MultiAZ": false,
            "EngineVersion": "15.2-limitless",
            "AutoMinorVersionUpgrade": true,
            "ReadReplicaDBInstanceIdentifiers": [],
            "LicenseModel": "postgresql-license",
            "OptionGroupMemberships": [
                {
                    "OptionGroupName": "default:aurora-postgresql-15",
                    "Status": "in-sync"
                }
            ],
            "PubliclyAccessible": false,
            "StorageType": "aurora-iopt1",
            "DbInstancePort": 0,
            "DBClusterIdentifier": "my-sv2-cluster",
            "StorageEncrypted": false,
            "DbiResourceId": "db-BIQTE3B3K3RM7M74SK5EXAMPLE",
            "CACertificateIdentifier": "rds-ca-rsa2048-g1",
            "DomainMemberships": [],
            "CopyTagsToSnapshot": false,
            "MonitoringInterval": 0,
            "PromotionTier": 1,
            "DBInstanceArn": "arn:aws:rds:us-west-2:123456789012:db:my-sv2-instance",
            "IAMDatabaseAuthenticationEnabled": false,
            "PerformanceInsightsEnabled": false,
            "DeletionProtection": false,
            "AssociatedRoles": [],
            "TagList": [],
            "CustomerOwnedIpEnabled": false,
            "BackupTarget": "region",
            "NetworkType": "IPV4",
            "StorageThroughput": 0,
            "CertificateDetails": {
                "CAIdentifier": "rds-ca-rsa2048-g1"
            },
            "DedicatedLogVolume": false
        }
    }

For more information, see `Using Aurora Serverless v2 <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html>`__ in the *Amazon Aurora User Guide*.
