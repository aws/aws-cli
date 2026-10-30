**To delete an elastic cluster snapshot**

The following ``delete-cluster-snapshot`` example deletes the specified Amazon DocumentDB elastic cluster snapshot. ::

    aws docdb-elastic delete-cluster-snapshot \
        --snapshot-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster-snapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "snapshot": {
            "adminUserName": "docdbadmin",
            "clusterArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "clusterCreationTime": "2026-10-29T06:15:23.077Z",
            "kmsKeyId": "AWS_OWNED_KMS_KEY",
            "snapshotArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster-snapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "snapshotCreationTime": "2026-10-29T06:53:34.014Z",
            "snapshotName": "docdb-elastic-snapshot",
            "snapshotType": "MANUAL",
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

For more information, see `Deleting an elastic cluster snapshot <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-manage-snapshots.html#elastic-delete-snapshot>`__ in the *Amazon DocumentDB Developer Guide*.
