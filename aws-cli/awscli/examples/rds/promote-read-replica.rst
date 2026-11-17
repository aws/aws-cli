**To promote a read replica**

The following ``promote-read-replica`` example promotes the specified read replica to become a standalone DB instance. ::

    aws rds promote-read-replica \
        --db-instance-identifier test-instance-repl

Output::

    {
        "DBInstance": {
            "DBInstanceArn": "arn:aws:rds:us-west-2:123456789012:db:test-instance-repl",
            "StorageType": "standard",
            "ReadReplicaSourceDBInstanceIdentifier": "test-instance",
            "DBInstanceStatus": "modifying"
        }
    }

For more information, see `Promoting a read replica to be a standalone DB instance <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.Promote.html>`__ in the *Amazon RDS User Guide*.
