**To start a relational database**

The following ``start-relational-database`` example starts the specified relational database. ::

    aws lightsail start-relational-database \
        --relational-database-name Database-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "Database-1",
                "resourceType": "RelationalDatabase",
                "createdAt": 1571695998.822,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "StartRelationalDatabase",
                "status": "Started",
                "statusChangedAt": 1571695998.822
            }
        ]
    }

For more information, see `Create and manage relational databases in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-databases.html>`__ in the *Amazon Lightsail User Guide*.
