**To get the events for a relational database**

The following ``get-relational-database-events`` example displays details about events in the last 17 hours (1020 minutes) for the specified relational database. ::

    aws lightsail get-relational-database-events \
        --relational-database-name Database-1 \
        --duration-in-minutes 1020

Output::

    {
        "relationalDatabaseEvents": [
            {
                "resource": "Database-1",
                "createdAt": 1571654146.553,
                "message": "Backing up Relational Database",
                "eventCategories": [
                    "backup"
                ]
            },
            {
                "resource": "Database-1",
                "createdAt": 1571654249.98,
                "message": "Finished Relational Database backup",
                "eventCategories": [
                    "backup"
                ]
            }
        ]
    }

For more information, see `Create and manage relational databases in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-databases.html>`__ in the *Amazon Lightsail User Guide*.
