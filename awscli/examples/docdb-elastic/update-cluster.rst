**To modify an elastic cluster**

The following ``update-cluster`` example changes the backup retention period of the specified Amazon DocumentDB elastic cluster to 7 days. ::

    aws docdb-elastic update-cluster \
        --cluster-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --backup-retention-period 7

Output::

    {
        "cluster": {
            "adminUserName": "docdbadmin",
            "authType": "PLAIN_TEXT",
            "backupRetentionPeriod": 1,
            "clusterArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "clusterEndpoint": "docdb-elastic-cluster-123456789012.us-west-2.docdb-elastic.amazonaws.com",
            "clusterName": "docdb-elastic-cluster",
            "createTime": "2026-10-29T06:15:23.077Z",
            "kmsKeyId": "AWS_OWNED_KMS_KEY",
            "preferredBackupWindow": "08:11-08:41",
            "preferredMaintenanceWindow": "Sun:10:26-Sun:10:56",
            "shardCapacity": 2,
            "shardCount": 1,
            "shardInstanceCount": 2,
            "shards": [
                {
                    "createTime": "2026-10-29T06:16:10.105Z",
                    "shardId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                    "status": "ACTIVE"
                }
            ],
            "status": "UPDATING",
            "subnetIds": [
                "subnet-0123456789abcdef0",
                "subnet-0123456789abcdef1"
            ],
            "vpcSecurityGroupIds": [
                "sg-0123456789abcdef0"
            ]
        }
    }

For more information, see `Modifying elastic cluster configurations <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-managing.html#elastic-modify>`__ in the *Amazon DocumentDB Developer Guide*.
