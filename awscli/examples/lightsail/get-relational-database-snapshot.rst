**To get information about a relational database snapshot**

The following ``get-relational-database-snapshot`` example displays details about the specified relational database snapshot. ::

    aws lightsail get-relational-database-snapshot \
        --relational-database-snapshot-name Database-1-1571350042

Output::

    {
        "relationalDatabaseSnapshot": {
            "name": "Database-1-1571350042",
            "arn": "arn:aws:lightsail:us-west-2:123456789012:RelationalDatabaseSnapshot/0389bbad-4b85-4c3d-9EXAMPLEaee3643d2",
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
            "fromRelationalDatabaseArn": "arn:aws:lightsail:us-west-2:123456789012:RelationalDatabase/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "fromRelationalDatabaseBundleId": "micro_1_0",
            "fromRelationalDatabaseBlueprintId": "mysql_8_0"
        }
    }

For more information, see `Back up your Lightsail database with snapshots <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-creating-a-database-snapshot.html>`__ in the *Amazon Lightsail User Guide*.
