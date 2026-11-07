**To create an elastic cluster**

The following ``create-cluster`` example creates an Amazon DocumentDB elastic cluster with one shard. The admin user password is read from a file named ``admin_user_password.txt``, which in this example is located in the current working directory. ::

    aws docdb-elastic create-cluster \
        --cluster-name docdb-elastic-cluster \
        --shard-capacity 2 \
        --shard-count 1 \
        --admin-user-name docdbadmin \
        --auth-type PLAIN_TEXT \
        --admin-user-password file://admin_user_password.txt

Output::

    {
        "cluster": {
            "adminUserName": "docdbadmin",
            "authType": "PLAIN_TEXT",
            "backupRetentionPeriod": 1,
            "clusterArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "clusterName": "docdb-elastic-cluster",
            "createTime": "2026-10-29T06:15:23.077191912Z",
            "kmsKeyId": "AWS_OWNED_KMS_KEY",
            "preferredBackupWindow": "08:11-08:41",
            "preferredMaintenanceWindow": "Sun:10:26-Sun:10:56",
            "shardCapacity": 2,
            "shardCount": 1,
            "shardInstanceCount": 2,
            "shards": [],
            "status": "CREATING",
            "subnetIds": [
                "subnet-0123456789abcdef0",
                "subnet-0123456789abcdef1"
            ],
            "vpcSecurityGroupIds": [
                "sg-0123456789abcdef0"
            ]
        }
    }

For more information, see `Get started with Amazon DocumentDB elastic clusters <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-get-started.html>`__ in the *Amazon DocumentDB Developer Guide*.
