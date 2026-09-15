**To describe the tenant databases in a DB snapshot**

The following ``describe-db-snapshot-tenant-databases`` example retrieves the details of the tenant databases contained in a snapshot of an RDS for Oracle CDB instance. ::

    aws rds describe-db-snapshot-tenant-databases \
        --db-snapshot-identifier final-snap-test

Output::

    {
        "DBSnapshotTenantDatabases": [
            {
                "DBSnapshotIdentifier": "final-snap-test",
                "DBInstanceIdentifier": "test-rds-oracle",
                "DbiResourceId": "db-ABCD1234EFGH5678IJKEXAMPLE",
                "EngineName": "oracle-se2-cdb",
                "SnapshotType": "manual",
                "TenantDBName": "ORCL",
                "MasterUsername": "admin",
                "TenantDatabaseResourceId": "tdb-QRST5678UVWX1234YZAB90CDEFGHIJ5678KLMN1234OPQEXAMPLE",
                "CharacterSetName": "AL16UTF16",
                "DBSnapshotTenantDatabaseARN": "arn:aws:rds:us-east-1:123456789012:snapshot-tenant-database:final-snap-test:tdb-qrst5678uvwx1234yzab90cdefghij5678klmn1234opqexample",
                "TagList": []
            },
            {
                "DBSnapshotIdentifier": "final-snap-test",
                "DBInstanceIdentifier": "test-rds-oracle",
                "DbiResourceId": "db-ABCD1234EFGH5678IJKEXAMPLE",
                "EngineName": "oracle-se2-cdb",
                "SnapshotType": "manual",
                "TenantDBName": "TENANT2",
                "MasterUsername": "tenantadmin",
                "TenantDatabaseResourceId": "tdb-ABCD1234EFGH5678IJKL90MNOPQRST1234UVWX5678YZAEXAMPLE",
                "CharacterSetName": "AL16UTF16",
                "DBSnapshotTenantDatabaseARN": "arn:aws:rds:us-east-1:123456789012:snapshot-tenant-database:final-snap-test:tdb-abcd1234efgh5678ijkl90mnopqrst1234uvwx5678yzaexample",
                "TagList": []
            }
        ]
    }

For more information, see `Restoring to a DB instance <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_RestoreFromSnapshot.html>`__ in the *Amazon RDS User Guide*.
