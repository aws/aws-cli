**To get the log streams for a relational database**

The following ``get-relational-database-log-streams`` example returns all of the available log streams for the specified relational database. ::

    aws lightsail get-relational-database-log-streams \
        --relational-database-name Database1

Output::

    {
        "logStreams": [
            "audit",
            "error",
            "general",
            "slowquery"
        ]
    }

For more information, see `Monitor MySQL query performance with general and slow query logs in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-enabling-mysql-general-and-slow-query-logs.html>`__ in the *Amazon Lightsail User Guide*.
