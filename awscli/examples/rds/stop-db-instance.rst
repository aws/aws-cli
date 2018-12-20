**To stop a DB instance**

This example stops a DB instance::

    aws rds stop-db-instance --db-instance-identifier test-instance

Output::

{
    "DBInstance": {

<...output omitted...>

        "DBInstanceStatus": "stopping",

<...output omitted...>

}
