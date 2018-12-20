**To restore a DB instance from a DB snapshot**

This example creates a new DB instance (*restored-test-instance*) from an existing DB snapshot (*test-instance-snap*)::

    aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier restored-test-instance \
    --db-snapshot-identifier test-instance-snap

Output::

{
    "DBInstance": {

<...output omitted...>

        "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:restored-test-instance",

<...output omitted...>

        "DBInstanceStatus": "creating",

}
