**To delete an elastic cluster**

The following ``delete-cluster`` example deletes the specified Amazon DocumentDB elastic cluster. ::

    aws docdb-elastic delete-cluster \
        --cluster-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444

Output::

    {
        "cluster": {
            "adminUserName": "docdbadmin",
            "authType": "PLAIN_TEXT",
            "backupRetentionPeriod": 7,
            "clusterArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
            "clusterEndpoint": "docdb-elastic-restored-cluster-123456789012.us-west-2.docdb-elastic.amazonaws.com",
            "clusterName": "docdb-elastic-restored-cluster",
            "createTime": "2026-10-29T10:23:55.467Z",
            "kmsKeyId": "AWS_OWNED_KMS_KEY",
            "preferredBackupWindow": "08:11-08:41",
            "preferredMaintenanceWindow": "Sun:10:26-Sun:10:56",
            "shardCapacity": 2,
            "shardCount": 1,
            "shardInstanceCount": 2,
            "shards": [
                {
                    "createTime": "2026-10-29T10:24:42.433Z",
                    "shardId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                    "status": "ACTIVE"
                }
            ],
            "status": "DELETING",
            "subnetIds": [
                "subnet-0123456789abcdef0",
                "subnet-0123456789abcdef1"
            ],
            "vpcSecurityGroupIds": [
                "sg-0123456789abcdef0"
            ]
        }
    }

For more information, see `Deleting an elastic cluster <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-managing.html#elastic-delete>`__ in the *Amazon DocumentDB Developer Guide*.
