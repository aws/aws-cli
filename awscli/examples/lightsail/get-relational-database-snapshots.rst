**To get information about all relational database snapshots**

The following ``get-relational-database-snapshots`` example displays details about all of the relational database snapshots in the configured AWS Region. ::

    aws lightsail get-relational-database-snapshots

Output::

    {
        "relationalDatabaseSnapshots": [
            {
                "name": "Database-1-1571350042",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:RelationalDatabaseSnapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "supportCode": "6EXAMPLE3362/ls-8EXAMPLE2ba7ad041451946fafc2ad19cfbd9eb2",
                "createdAt": 1571350046.238,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "RelationalDatabaseSnapshot",
                "tags": [],
                "engine": "mysql",
                "engineVersion": "8.0.16",
                "sizeInGb": 40,
                "state": "available",
                "fromRelationalDatabaseName": "Database-1",
                "fromRelationalDatabaseArn": "arn:aws:lightsail:us-west-2:123456789012:RelationalDatabase/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "fromRelationalDatabaseBundleId": "micro_1_0",
                "fromRelationalDatabaseBlueprintId": "mysql_8_0"
            },
            {
                "name": "Database1-Console",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:RelationalDatabaseSnapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "supportCode": "6EXAMPLE3362/ls-9EXAMPLE14b000d34c8d1c432734e137612d5b5c",
                "createdAt": 1571249981.025,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "RelationalDatabaseSnapshot",
                "tags": [
                    {
                        "key": "test"
                    }
                ],
                "engine": "mysql",
                "engineVersion": "5.6.44",
                "sizeInGb": 40,
                "state": "available",
                "fromRelationalDatabaseName": "Database1",
                "fromRelationalDatabaseArn": "arn:aws:lightsail:us-west-2:123456789012:RelationalDatabase/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "fromRelationalDatabaseBundleId": "micro_1_0",
                "fromRelationalDatabaseBlueprintId": "mysql_5_6"
            }
        ]
    }

For more information, see `Back up your Lightsail database with snapshots <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-creating-a-database-snapshot.html>`__ in the *Amazon Lightsail User Guide*.
