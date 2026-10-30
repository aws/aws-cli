**To copy an elastic cluster snapshot**

The following ``copy-cluster-snapshot`` example copies the specified Amazon DocumentDB elastic cluster snapshot to a new snapshot named ``docdb-elastic-snapshot-copy``. ::

    aws docdb-elastic copy-cluster-snapshot \
        --snapshot-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster-snapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --target-snapshot-name docdb-elastic-snapshot-copy

Output::

    {
        "snapshot": {
            "clusterArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "kmsKeyId": "AWS_OWNED_KMS_KEY",
            "snapshotArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster-snapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "snapshotCreationTime": "2026-10-29T07:15:13.566107154Z",
            "snapshotName": "docdb-elastic-snapshot-copy",
            "snapshotType": "MANUAL",
            "status": "COPYING"
        }
    }

For more information, see `Copying an elastic cluster snapshot <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-manage-snapshots.html#elastic-copy-snapshot>`__ in the *Amazon DocumentDB Developer Guide*.
