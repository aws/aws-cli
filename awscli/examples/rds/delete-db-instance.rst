**To delete a DB instance**

This example deletes the specified DB instance, but only after creating a final DB snapshot named ``test-instance-final-snap``. ::

    aws rds delete-db-instance --db-instance-identifier test-instance \
        --final-db-snapshot-identifier test-instance-final-snap

Output::

    {
        "DBInstance": {
            "DBInstanceIdentifier": "test-instance",
            "DBInstanceStatus": "deleting",
            <...some output omitted...>
        }
    }
