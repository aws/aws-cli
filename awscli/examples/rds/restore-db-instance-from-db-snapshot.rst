**To restore a DB instance from a DB snapshot**

The following ``restore-db-instance-from-db-snapshot`` example creates a new DB instance named ``restored-test-instance`` from the specified DB snapshot. ::

    aws rds restore-db-instance-from-db-snapshot \
        --db-instance-identifier restored-test-instance \
        --db-snapshot-identifier test-instance-snap

Output::

    {
        "DBInstance": {
            "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:restored-test-instance",
            "DBInstanceStatus": "creating",
            ...some output truncated...
        }
    }
