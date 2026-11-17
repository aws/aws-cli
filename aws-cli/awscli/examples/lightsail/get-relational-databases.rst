**To get information about all relational databases**

The following ``get-relational-databases`` example displays details about all of the relational databases in the configured AWS Region. ::

    aws lightsail get-relational-databases

Output::

    {
        "relationalDatabases": [
            {
                "name": "MySQL",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:RelationalDatabase/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "supportCode": "6EXAMPLE3362/ls-3EXAMPLEa995d8c3b06b4501356e5f2f28e1aeba",
                "createdAt": 1554306019.155,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "resourceType": "RelationalDatabase",
                "tags": [],
                "relationalDatabaseBlueprintId": "mysql_8_0",
                "relationalDatabaseBundleId": "micro_1_0",
                "masterDatabaseName": "dbmaster",
                "hardware": {
                    "cpuCount": 1,
                    "diskSizeInGb": 40,
                    "ramSizeInGb": 1.0
                },
                "state": "available",
                "backupRetentionEnabled": true,
                "pendingModifiedValues": {},
                "engine": "mysql",
                "engineVersion": "8.0.15",
                "latestRestorableTime": 1571686200.0,
                "masterUsername": "dbmasteruser",
                "parameterApplyStatus": "in-sync",
                "preferredBackupWindow": "07:51-08:21",
                "preferredMaintenanceWindow": "tue:12:18-tue:12:48",
                "publiclyAccessible": true,
                "masterEndpoint": {
                    "port": 3306,
                    "address": "ls-3EXAMPLEa995d8c3b06b4501356e5f2fEXAMPLEa.czowadgeezqi.us-west-2.rds.amazonaws.com"
                },
                "pendingMaintenanceActions": []
            },
            {
                "name": "Postgres",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:RelationalDatabase/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "supportCode": "6EXAMPLE3362/ls-3EXAMPLEb4fffb5cec056220c734713e14bd5fcd",
                "createdAt": 1554306000.814,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "resourceType": "RelationalDatabase",
                "tags": [],
                "relationalDatabaseBlueprintId": "postgres_11",
                "relationalDatabaseBundleId": "micro_1_0",
                "masterDatabaseName": "dbmaster",
                "hardware": {
                    "cpuCount": 1,
                    "diskSizeInGb": 40,
                    "ramSizeInGb": 1.0
                },
                "state": "available",
                "backupRetentionEnabled": true,
                "pendingModifiedValues": {},
                "engine": "postgres",
                "engineVersion": "11.1",
                "latestRestorableTime": 1571686339.0,
                "masterUsername": "dbmasteruser",
                "parameterApplyStatus": "in-sync",
                "preferredBackupWindow": "06:19-06:49",
                "preferredMaintenanceWindow": "sun:10:19-sun:10:49",
                "publiclyAccessible": false,
                "masterEndpoint": {
                    "port": 5432,
                    "address": "ls-3EXAMPLEb4fffb5cec056220c734713eEXAMPLEd.czowadgeezqi.us-west-2.rds.amazonaws.com"
                },
                "pendingMaintenanceActions": []
            }
        ]
    }

For more information, see `Create and manage relational databases in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-databases.html>`__ in the *Amazon Lightsail User Guide*.
