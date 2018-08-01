**To create a DB instance**

This example launches a new DB instance::

    aws rds create-db-instance \
    --allocated-storage 20 --db-instance-class db.m1.small \
    --db-instance-identifier test-instance --engine mysql \
    --enable-cloudwatch-logs-exports '["audit","error","general","slowquery"]' \
    --master-username master --master-user-password secret99

Output::

{
    "DBInstance": {
        "DBInstanceIdentifier": "test-instance",
        "DBInstanceClass": "db.m1.small",
        "Engine": "mysql",
        "DBInstanceStatus": "creating",
        "MasterUsername": "master",
        "AllocatedStorage": 20,
        "PreferredBackupWindow": "10:27-10:57",
        "BackupRetentionPeriod": 1,
        "DBSecurityGroups": [],
        "VpcSecurityGroups": [
            {
                "VpcSecurityGroupId": "sg-f839b688",
                "Status": "active"
            }
        ],
        "DBParameterGroups": [
            {
                "DBParameterGroupName": "default.mysql5.6",
                "ParameterApplyStatus": "in-sync"
            }
        ],
        "DBSubnetGroup": {
            "DBSubnetGroupName": "default",
            "DBSubnetGroupDescription": "default",
            "VpcId": "vpc-136a4c6a",
            "SubnetGroupStatus": "Complete",
            "Subnets": [
                {
                    "SubnetIdentifier": "subnet-cbfff283",
                    "SubnetAvailabilityZone": {
                        "Name": "us-east-1b"
                    },
                    "SubnetStatus": "Active"
                },
                {
                    "SubnetIdentifier": "subnet-d7c825e8",
                    "SubnetAvailabilityZone": {
                        "Name": "us-east-1e"
                    },
                    "SubnetStatus": "Active"
                },
                {
                    "SubnetIdentifier": "subnet-6746046b",
                    "SubnetAvailabilityZone": {
                        "Name": "us-east-1f"
                    },
                    "SubnetStatus": "Active"
                },
                {
                    "SubnetIdentifier": "subnet-bac383e0",
                    "SubnetAvailabilityZone": {
                        "Name": "us-east-1c"
                    },
                    "SubnetStatus": "Active"
                },
                {
                    "SubnetIdentifier": "subnet-42599426",
                    "SubnetAvailabilityZone": {
                        "Name": "us-east-1d"
                    },
                    "SubnetStatus": "Active"
                },
                {
                    "SubnetIdentifier": "subnet-da327bf6",
                    "SubnetAvailabilityZone": {
                        "Name": "us-east-1a"
                    },
                    "SubnetStatus": "Active"
                }
            ]
        },
        "PreferredMaintenanceWindow": "sat:05:47-sat:06:17",
        "PendingModifiedValues": {
            "MasterUserPassword": "****",
            "PendingCloudwatchLogsExports": {
                "LogTypesToEnable": [
                    "audit",
                    "error",
                    "general",
                    "slowquery"
                ]
            }
        },
        "MultiAZ": false,
        "EngineVersion": "5.6.39",
        "AutoMinorVersionUpgrade": true,
        "ReadReplicaDBInstanceIdentifiers": [],
        "LicenseModel": "general-public-license",
        "OptionGroupMemberships": [
            {
                "OptionGroupName": "default:mysql-5-6",
                "Status": "in-sync"
            }
        ],
        "PubliclyAccessible": true,
        "StorageType": "standard",
        "DbInstancePort": 0,
        "StorageEncrypted": false,
        "DbiResourceId": "db-ETDZIIXHEWY5N7GXVC4SH7H5IA",
        "CACertificateIdentifier": "rds-ca-2015",
        "DomainMemberships": [],
        "CopyTagsToSnapshot": false,
        "MonitoringInterval": 0,
        "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:test-instance",
        "IAMDatabaseAuthenticationEnabled": false,
        "PerformanceInsightsEnabled": false
    }
}

