**To describe status of table restore requests from a cluster snapshot**

The following ``describe-table-restore-status`` example displays details for table restore requests made for the specified cluster. ::

    aws redshift describe-table-restore-status \
        --cluster-identifier mycluster

Output::

    {
        "TableRestoreStatusDetails": [
            {
                "TableRestoreRequestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Status": "IN_PROGRESS",
                "RequestTime": "2019-12-27T18:22:12.257Z",
                "ClusterIdentifier": "mycluster",
                "SnapshotIdentifier": "mysnapshotid",
                "SourceDatabaseName": "dev",
                "SourceSchemaName": "public",
                "SourceTableName": "mytable",
                "TargetDatabaseName": "dev",
                "TargetSchemaName": "public",
                "NewTableName": "mytable-clone"
            }
        ]
    }

For more information, see `Restoring a Table from a Snapshot <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-snapshot-restore-table-from-snapshot.html>`__ in the *Amazon Redshift Cluster Management Guide*.
