**To modify a DB instance**

The following ``modify-db-instance`` example changes the instance class of the specified running DB instance. The ``--apply-immediately`` parameter causes the DB engine to be replaced immediately, instead of waiting until the next maintenance window. ::

    aws rds modify-db-instance \
        --db-instance-identifier test-instance \
        --db-instance-class db.m1.large \
        --apply-immediately

Output::

    {
        "DBInstance": {
            "DBInstanceIdentifier": "test-instance",
            "DBInstanceClass": "db.m1.small",
            "Engine": "mysql",
            "DBInstanceStatus": "modifying",
            <...output omitted...>
            "PendingModifiedValues": {
                "DBInstanceClass": "db.m1.large"
            }
        <...some output omitted...>
        }
    }
