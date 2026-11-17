**To start a DB instance**

The following ``start-db-instance`` example starts the specified DB instance. ::

    aws rds start-db-instance \
        --db-instance-identifier test-instance

Output::

    {
        "DBInstance": {
            "DBInstanceIdentifier": "test-instance",
            "DBInstanceStatus": "starting"
        }
    }

For more information, see `Starting an Amazon RDS DB instance that was previously stopped <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_StartInstance.html>`__ in the *Amazon RDS User Guide*.
