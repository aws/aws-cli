**To modify a DB instance**

This example modifies the instance class of a running DB instance (*test-instance*)::

    aws rds modify-db-instance --db-instance-identifier test-instance \
    --db-instance-class db.m1.large --apply-immediately

The *--apply-immediately* parameter causes the DB engine to be replaced immediately, instead of waiting until the next maintenance window. 

Output::
{
    "DBInstance": {
        "DBInstanceIdentifier": "test-instance",
        "DBInstanceClass": "db.m1.small",
        "Engine": "mysql",
        "DBInstanceStatus": "modifying",
        <...output omitted...>
        "PendingModifiedValues": {
            "DBInstanceClass": "db.m1.large"
        },

<...output omitted...>

}
