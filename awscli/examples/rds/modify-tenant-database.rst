**To rename a tenant database**

The following ``modify-tenant-database`` example renames a tenant database in an RDS for Oracle CDB instance. ::

    aws rds modify-tenant-database \
        --db-instance-identifier test-rds-oracle \
        --tenant-db-name orcl \
        --new-tenant-db-name tenant2

Output::

    {
        "TenantDatabase": {
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
            "PendingModifiedValues": {
                "TenantDBName": "TENANT2"
            },
            "TagList": []
        }
    }

For more information, see `Modifying an RDS for Oracle tenant database <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/oracle-cdb-configuring.modifying.pdb.html>`__ in the *Amazon RDS User Guide*.
