**To restore an elastic cluster from a snapshot**

The following ``restore-cluster-from-snapshot`` example creates a new Amazon DocumentDB elastic cluster named ``docdb-elastic-restored-cluster`` from the specified snapshot. ::

    aws docdb-elastic restore-cluster-from-snapshot \
        --cluster-name docdb-elastic-restored-cluster \
        --snapshot-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster-snapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "cluster": {
            "adminUserName": "docdbadmin",
            "authType": "PLAIN_TEXT",
            "backupRetentionPeriod": 7,
            "clusterArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
            "clusterName": "docdb-elastic-restored-cluster",
            "createTime": "2026-10-29T10:23:55.467462495Z",
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

For more information, see `Restoring an elastic cluster from a snapshot <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-manage-snapshots.html#elastic-restore-snapshot>`__ in the *Amazon DocumentDB Developer Guide*.
