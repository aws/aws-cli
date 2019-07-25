**To restore a DB instance to a point in time**

The following ``restore-db-instance-to-point-in-time`` example restores ``test-instance`` to a new DB instance named ``restored-test-instance``, as of the specified time. :: 

    aws rds restore-db-instance-to-point-in-time \
        --source-db-instance-identifier test-instance \
        --target-db-instance restored-test-instance \
        --restore-time 2018-07-30T23:45:00.000Z

Output::

    {
        "DBInstance": {
            "AllocatedStorage": 20,
            "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:restored-test-instance",
            "DBInstanceStatus": "creating",
            "DBInstanceIdentifier": "restored-test-instance",
            ...some output truncated...
        }
    }
