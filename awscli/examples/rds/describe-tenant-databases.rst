**To describe the tenant databases in a DB instance**

The following ``describe-tenant-databases`` example retrieves the details of the tenant databases in an RDS for Oracle CDB instance. ::

    aws rds describe-tenant-databases \
        --db-instance-identifier test-rds-oracle

Output::

    {
        "TenantDatabases": [
            {
                "TenantDatabaseCreateTime": "2026-09-12T16:02:18.011000+00:00",
                "DBInstanceIdentifier": "test-rds-oracle",
                "TenantDBName": "ORCL",
                "Status": "available",
                "MasterUsername": "admin",
                "DbiResourceId": "db-ABCD1234EFGH5678IJKEXAMPLE",
                "TenantDatabaseResourceId": "tdb-QRST5678UVWX1234YZAB90CDEFGHIJ5678KLMN1234OPQEXAMPLE",
                "TenantDatabaseARN": "arn:aws:rds:us-east-1:123456789012:tenant-database:tdb-qrst5678uvwx1234yzab90cdefghij5678klmn1234opqexample",
                "CharacterSetName": "AL32UTF8",
                "NcharCharacterSetName": "AL16UTF16",
                "DeletionProtection": false,
                "PendingModifiedValues": {},
                "TagList": []
            }
        ]
    }

For more information, see `Viewing tenant database details <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/oracle-cdb-configuring.describing.pdb.html>`__ in the *Amazon RDS User Guide*.
