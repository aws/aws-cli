**To delete a snapshot of a managed database**

The following ``delete-relational-database-snapshot`` example deletes the specified snapshot of a managed database. ::

    aws lightsail delete-relational-database-snapshot \
        --relational-database-snapshot-name Database-Oregon-1-1566839359

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "Database-Oregon-1-1566839359",
                "resourceType": "RelationalDatabaseSnapshot",
                "createdAt": 1569875293.58,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationType": "DeleteRelationalDatabaseSnapshot",
                "status": "Succeeded",
                "statusChangedAt": 1569875293.58
            }
        ]
    }

For more information, see `Delete unused Lightsail snapshots to avoid monthly charges <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-deleting-snapshots.html>`__ in the *Amazon Lightsail User Guide*.
