**To create a DB instance read replica**

This example creates a read replica of an existing DB instance (*test-instance*).  The read replica is named *test-instance-repl*::

    aws rds create-db-instance-read-replica \
    --db-instance-identifier test-instance-repl \
    --source-db-instance-identifier test-instance 

Output::

{
    "DBInstance": {
        "IAMDatabaseAuthenticationEnabled": false,
        "MonitoringInterval": 0,
        "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:test-instance-repl",
        "ReadReplicaSourceDBInstanceIdentifier": "test-instance",

<...output omitted...>

        "DBInstanceIdentifier": "test-instance-repl",

<...output omitted...>

}

