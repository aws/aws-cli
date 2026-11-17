**To delete a managed database**

The following ``delete-relational-database`` example deletes the specified managed database. ::

    aws lightsail delete-relational-database \
        --relational-database-name Database-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "Database-1",
                "resourceType": "RelationalDatabase",
                "createdAt": 1569875210.999,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "DeleteRelationalDatabase",
                "status": "Started",
                "statusChangedAt": 1569875210.999
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "Database-1",
                "resourceType": "RelationalDatabase",
                "createdAt": 1569875211.029,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "Database-1-FinalSnapshot-1569875210793",
                "operationType": "CreateRelationalDatabaseSnapshot",
                "status": "Started",
                "statusChangedAt": 1569875211.029
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "resourceName": "Database-1-FinalSnapshot-1569875210793",
                "resourceType": "RelationalDatabaseSnapshot",
                "createdAt": 1569875211.029,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "Database-1",
                "operationType": "CreateRelationalDatabaseSnapshot",
                "status": "Started",
                "statusChangedAt": 1569875211.029
            }
        ]
    }

For more information, see `Delete a Lightsail database and create a final snapshot <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-deleting-your-database.html>`__ in the *Amazon Lightsail User Guide*.
