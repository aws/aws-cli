**To describe Amazon RDS DB instances**

The following ``describe-db-instances`` command lists all of the DB instances for an AWS account::

    aws rds describe-db-instances

This command outputs a JSON block that lists the DB instances::

{
    "DBInstances": [
        {
            "PubliclyAccessible": false,
            "MasterUsername": "mymasteruser",
            "MonitoringInterval": 0,
            "LicenseModel": "general-public-license",
            "VpcSecurityGroups": [
                {
                    "Status": "active",
                    "VpcSecurityGroupId": "sg-1203dc23"
                }
            ],
            "InstanceCreateTime": "2016-06-13T20:09:43.836Z",
            "CopyTagsToSnapshot": false,
            "OptionGroupMemberships": [
                {
                    "Status": "in-sync",
                    "OptionGroupName": "default:mysql-5-6"
                }
            ],
            "PendingModifiedValues": {},
            "Engine": "mysql",
            "MultiAZ": false,
            "LatestRestorableTime": "2016-06-13T21:00:00Z",
            "DBSecurityGroups": [],
            "DBParameterGroups": [
                {
                    "DBParameterGroupName": "default.mysql5.6",
                    "ParameterApplyStatus": "in-sync"
                }
            ],
            "AutoMinorVersionUpgrade": true,
            "PreferredBackupWindow": "08:03-08:33",
            "DBSubnetGroup": {
                "Subnets": [
                    {
                        "SubnetStatus": "Active",
                        "SubnetIdentifier": "subnet-6a88c933",
                        "SubnetAvailabilityZone": {
                            "Name": "us-east-1a"
                        }
                    },
                    {
                        "SubnetStatus": "Active",
                        "SubnetIdentifier": "subnet-98302fa2",
                        "SubnetAvailabilityZone": {
                            "Name": "us-east-1e"
                        }
                    },
                    {
                        "SubnetStatus": "Active",
                        "SubnetIdentifier": "subnet-159bf13e",
                        "SubnetAvailabilityZone": {
                            "Name": "us-east-1c"
                        }
                    },
                    {
                        "SubnetStatus": "Active",
                        "SubnetIdentifier": "subnet-67466810",
                        "SubnetAvailabilityZone": {
                            "Name": "us-east-1d"
                        }
                    }
                ],
                "DBSubnetGroupName": "default",
                "VpcId": "vpc-a2b3aab6",
                "DBSubnetGroupDescription": "default",
                "SubnetGroupStatus": "Complete"
            },
            "ReadReplicaDBInstanceIdentifiers": [],
            "AllocatedStorage": 50,
            "BackupRetentionPeriod": 7,
            "DBName": "sample",
            "PreferredMaintenanceWindow": "sat:04:35-sat:05:05",
            "Endpoint": {
                "Port": 3306,
                "Address": "mydbinstance-1.ctrzran0rynq.us-east-1.rds.amazonaws.com"
            },
            "DBInstanceStatus": "stopped",
            "EngineVersion": "5.6.27",
            "AvailabilityZone": "us-east-1e",
            "DomainMemberships": [],
            "StorageType": "standard",
            "DbiResourceId": "db-B3COT4JG5UC4IACGJ72IGR34RM",
            "CACertificateIdentifier": "rds-ca-2015",
            "StorageEncrypted": false,
            "DBInstanceClass": "db.t2.micro",
            "DbInstancePort": 0,
            "DBInstanceIdentifier": "mydbinstance-1"
        }
    ]
}

