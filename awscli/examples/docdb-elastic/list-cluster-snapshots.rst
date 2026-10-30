**To list the snapshots of an elastic cluster**

The following ``list-cluster-snapshots`` example lists the snapshots of the specified Amazon DocumentDB elastic cluster. ::

    aws docdb-elastic list-cluster-snapshots \
        --cluster-arn arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "snapshots": [
            {
                "clusterArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "snapshotArn": "arn:aws:docdb-elastic:us-west-2:123456789012:cluster-snapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "snapshotCreationTime": "2026-10-29T06:53:34.018Z",
                "snapshotName": "docdb-elastic-snapshot",
                "status": "ACTIVE"
            }
        ]
    }

For more information, see `Viewing an elastic cluster snapshot <https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-manage-snapshots.html#elastic-view-snapshot>`__ in the *Amazon DocumentDB Developer Guide*.
