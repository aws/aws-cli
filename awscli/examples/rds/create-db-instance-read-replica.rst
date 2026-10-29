**To create a DB instance read replica**

The following ``create-db-instance-read-replica`` example creates a read replica of an existing DB instance named ``test-instance``. The read replica is named ``test-instance-repl``. ::

    aws rds create-db-instance-read-replica \
        --db-instance-identifier test-instance-repl \
        --source-db-instance-identifier test-instance 

Output::

    {
        "DBInstance": {
            "IAMDatabaseAuthenticationEnabled": false,
            "MonitoringInterval": 0,
            "DBInstanceArn": "arn:aws:rds:us-west-2:123456789012:db:test-instance-repl",
            "ReadReplicaSourceDBInstanceIdentifier": "test-instance",
            "DBInstanceIdentifier": "test-instance-repl"
        }
    }

For more information, see `Creating a read replica <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.Create.html>`__ in the *Amazon RDS User Guide*.
