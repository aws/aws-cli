**To create an Amazon RDS DB instance**

The following ``create-db-instance`` command launches a new Amazon RDS DB instance::

    aws rds create-db-instance --db-instance-identifier sg-cli-test \
    --allocated-storage 20 --db-instance-class db.m1.small --engine mysql \
    --master-username myawsuser --master-user-password myawsuser

In the preceding example, the DB instance is created with 20 Gb of standard storage and has a DB engine class of
db.m1.small. The master username and master password are provided.

This command outputs a JSON block that indicates that the DB instance was created::

    {
        "DBInstance": {
            "Engine": "mysql",
            "MultiAZ": false,
            "DBSecurityGroups": [
                {
                    "Status": "active",
                    "DBSecurityGroupName": "default"
                }
            ],
            "DBInstanceStatus": "creating",
            "DBParameterGroups": [
                {
                    "DBParameterGroupName": "default.mysql5.6",
                    "ParameterApplyStatus": "in-sync"
                }
            ],
            "MasterUsername": "myawsuser",
            "LicenseModel": "general-public-license",
            "OptionGroupMemberships": [
                {
                    "Status": "in-sync",
                    "OptionGroupName": "default:mysql-5-6"
                }
            ],
            "AutoMinorVersionUpgrade": true,
            "PreferredBackupWindow": "11:58-12:28",
            "VpcSecurityGroups": [],
            "PubliclyAccessible": true,
            "PreferredMaintenanceWindow": "sat:13:10-sat:13:40",
            "AllocatedStorage": 20,
            "EngineVersion": "5.6.13",
            "DBInstanceClass": "db.m1.small",
            "ReadReplicaDBInstanceIdentifiers": [],
            "BackupRetentionPeriod": 1,
            "DBInstanceIdentifier": "sg-cli-test",
            "PendingModifiedValues": {
                "MasterUserPassword": "****"
            }
        }
    }

