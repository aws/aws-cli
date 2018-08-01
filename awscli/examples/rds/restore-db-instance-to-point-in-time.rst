**To restore a DB instance to a point in time**

This example restores *test-instance* to a new DB instance (*restored-test-instance*), as of a particular point in time:: 

    aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier test-instance \
    --target-db-instance restored-test-instance \
    --restore-time 2018-07-30T23:45:00.000Z


Output::

{
    "DBInstance": {
        "AllocatedStorage": 20,
        "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:restored-test-instance",

<...output omitted...>

        "DBInstanceStatus": "creating",
        "DBInstanceIdentifier": "restored-test-instance",

<...output omitted...>

}

