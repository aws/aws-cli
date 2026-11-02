**To reboot a relational database**

The following ``reboot-relational-database`` example reboots the specified relational database. ::

    aws lightsail reboot-relational-database \
        --relational-database-name Database-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "Database-1",
                "resourceType": "RelationalDatabase",
                "createdAt": 1571694532.91,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "",
                "operationType": "RebootRelationalDatabase",
                "status": "Started",
                "statusChangedAt": 1571694532.91
            }
        ]
    }

For more information, see `Create and manage relational databases in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-databases.html>`__ in the *Amazon Lightsail User Guide*.
