**To create a managed database**

The following ``create-relational-database`` example creates a managed database in the specified AWS Region and Availability Zone, using the MySQL 5.6 database engine (mysql_5_6), and the $15 USD standard database bundle (micro_1_0). The managed database is pre-populated a master user name, and is not publicly accessible. ::

    aws lightsail create-relational-database \
        --relational-database-name Database-1 \
        --availability-zone us-west-2a \
        --relational-database-blueprint-id mysql_5_6 \
        --relational-database-bundle-id micro_1_0 \
        --master-database-name dbmaster \
        --master-username user \
        --no-publicly-accessible

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "Database-1",
                "resourceType": "RelationalDatabase",
                "createdAt": 1569450017.244,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "CreateRelationalDatabase",
                "status": "Started",
                "statusChangedAt": 1569450018.637
            }
        ]
    }

For more information, see `Create a Lightsail database <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-creating-a-database.html>`__ in the *Amazon Lightsail User Guide*.
