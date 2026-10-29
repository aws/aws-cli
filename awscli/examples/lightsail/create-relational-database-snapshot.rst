**To create a snapshot of a managed database**

The following ``create-relational-database-snapshot`` example creates a snapshot of the specified managed database. ::

    aws lightsail create-relational-database-snapshot \
        --relational-database-name Database1 \
        --relational-database-snapshot-name RelationalDatabaseSnapshot1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "RelationalDatabaseSnapshot1",
                "resourceType": "RelationalDatabaseSnapshot",
                "createdAt": 1569868074.645,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "Database1",
                "operationType": "CreateRelationalDatabaseSnapshot",
                "status": "Started",
                "statusChangedAt": 1569868074.645
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "Database1",
                "resourceType": "RelationalDatabase",
                "createdAt": 1569868074.645,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "RelationalDatabaseSnapshot1",
                "operationType": "CreateRelationalDatabaseSnapshot",
                "status": "Started",
                "statusChangedAt": 1569868074.645
            }
        ]
    }

For more information, see `Back up your Lightsail database with snapshots <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-creating-a-database-snapshot.html>`__ in the *Amazon Lightsail User Guide*.
