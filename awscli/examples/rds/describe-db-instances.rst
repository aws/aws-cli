**To describe a DB instance**

This example describes a single DB instance (*test-instance*)::

    aws rds describe-db-instances --db-instance-identifier test-instance

Output::
{
    "DBInstance": {
        "DBInstanceIdentifier": "test-instance",
        "DBInstanceClass": "db.m1.small",
        "Engine": "mysql",
        "DBInstanceStatus": "available",
        "MasterUsername": "myawsuser",
        "Endpoint": {
            "Address": "test-instance.cdgmuqiadpid.us-east-1.rds.amazonaws.com",
            "Port": 3306,
            "HostedZoneId": "Z2R2ITUGPM61AM"
        },

<...output omitted...>

}
