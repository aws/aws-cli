**To stop a DB instance**

The following ``stop-db-instance`` example stops the specified DB instance. ::

    aws rds stop-db-instance \
        --db-instance-identifier test-instance

Output::

    {
        "DBInstance": {
            "DBInstanceIdentifier": "test-instance",
            "DBInstanceStatus": "stopping"
        }
    }

For more information, see `Stopping an Amazon RDS DB instance temporarily <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_StopInstance.html>`__ in the *Amazon RDS User Guide*.
