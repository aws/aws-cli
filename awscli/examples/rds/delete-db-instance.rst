**To delete a DB instance**

This example deletes a DB instance (*test-instance*), but only after creating a final DB snapshot (*test-instance-final-snap*)::

    aws rds delete-db-instance --db-instance-identifier test-instance \
    --final-db-snapshot-identifier test-instance-final-snap

Output::

{
    "DBInstance": {

<...output omitted...>

        "DBInstanceIdentifier": "test-instance",

<...output omitted...>

        "DBInstanceStatus": "deleting",

<...output omitted...>

}
