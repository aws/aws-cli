**To create a manual snapshot of an elastic cluster**

The following ``create-cluster-snapshot`` example creates a manual snapshot named ``docdb-elastic-snapshot`` of the specified Amazon DocumentDB elastic cluster. ::

    aws docdb-elastic create-cluster-snapshot \
        --cluster-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --snapshot-name docdb-elastic-snapshot

Output::

    {
        "snapshot": {
            "clusterArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "clusterCreationTime": "2026-10-29T06:15:23.077Z",
            "kmsKeyId": "AWS_OWNED_KMS_KEY",
            "snapshotArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster-snapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "snapshotCreationTime": "2026-10-29T06:53:34.014442428Z",
            "snapshotName": "docdb-elastic-snapshot",
            "snapshotType": "MANUAL",
            "status": "CREATING"
        }
    }

For more information, see `Creating a manual elastic cluster snapshot <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-manage-snapshots.html#elastic-create-snapshot>`__ in the *Amazon DocumentDB Developer Guide*.
