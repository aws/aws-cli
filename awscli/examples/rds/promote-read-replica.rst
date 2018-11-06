**To promote a read replica**

This example promotes a read replica (*test-instance-repl*) so that it becomes a standalone DB instance::

    aws rds promote-read-replica --db-instance-identifier test-instance-repl

Output::

{
    "DBInstance": {
        "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:test-instance-repl",
        "StorageType": "standard",
        "ReadReplicaSourceDBInstanceIdentifier": "test-instance",

<...output omitted...>

        "DBInstanceStatus": "modifying",

<...output omitted...>

}
