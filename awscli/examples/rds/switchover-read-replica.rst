**To switch over a read replica**

The following ``switchover-read-replica`` example promotes the specified Oracle read replica to be the new primary database. Specify the identifier of the read replica that you're promoting. ::

    aws rds switchover-read-replica \
        --db-instance-identifier rds-oracle-reader

Output::

    {
        "DBInstance": {
            "DBInstanceIdentifier": "rds-oracle-reader",
            "DBInstanceStatus": "available",
            "Engine": "oracle-ee",
            "ReadReplicaSourceDBInstanceIdentifier": "rds-oracle-testdb",
            "ReplicaMode": "open-read-only",
            "StatusInfos": [
                {
                    "StatusType": "read replication",
                    "Normal": true,
                    "Status": "replicating"
                }
            ],
            "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:rds-oracle-reader",
            ...some output truncated...
        }
    }

For more information, see `Initiating the Oracle Data Guard switchover <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/oracle-switchover.initiating.html>`__ in the *Amazon RDS User Guide*.
