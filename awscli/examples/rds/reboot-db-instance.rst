**To reboot a DB instance**

The following ``reboot-db-instance`` example starts a reboot of the specified DB instance. ::

    aws rds reboot-db-instance \
        --db-instance-identifier test-instance

Output::

    {
        "DBInstance": {
            "DBInstanceIdentifier": "test-instance",
            "DBInstanceClass": "db.m1.small",
            "Engine": "mysql",
            "DBInstanceStatus": "rebooting",
            "MasterUsername": "myawsuser",
            "Endpoint": {
                "Address": "test-instance.cdgmuqiadpid.us-east-1.rds.amazonaws.com",
                "Port": 3306,
                "HostedZoneId": "Z2R2ITUGPM61AM"
            },
            <...some output omitted...>
        }
    }
