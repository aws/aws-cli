**To start a DB instance**

This example starts a DB instance::

    aws rds start-db-instance --db-instance-identifier test-instance

Output::

{
    "DBInstance": {

<...output omitted...>

        "DBInstanceStatus": "starting",

<...output omitted...>

}
