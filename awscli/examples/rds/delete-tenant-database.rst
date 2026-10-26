**To delete a tenant database**

The following ``delete-tenant-database`` example deletes a tenant database from an RDS for Oracle CDB instance and takes a final snapshot of it. ::

    aws rds delete-tenant-database \
        --db-instance-identifier test-rds-oracle \
        --tenant-db-name tenant2 \
        --final-db-snapshot-identifier final-snap-test

Output::

    {
        "TenantDatabase": {
            "TenantDatabaseCreateTime": "2026-09-12T16:12:32.429000+00:00",
            "DBInstanceIdentifier": "test-rds-oracle",
            "TenantDBName": "TENANT2",
            "Status": "deleting",
            "MasterUsername": "tenantadmin",
            "DbiResourceId": "db-ABCD1234EFGH5678IJKEXAMPLE",
            "TenantDatabaseResourceId": "tdb-ABCD1234EFGH5678IJKL90MNOPQRST1234UVWX5678YZAEXAMPLE",
            "TenantDatabaseARN": "arn:aws:rds:us-east-1:123456789012:tenant-database:tdb-abcd1234efgh5678ijkl90mnopqrst1234uvwx5678yzaexample",
            "CharacterSetName": "AL32UTF8",
            "NcharCharacterSetName": "AL16UTF16",
            "DeletionProtection": false,
            "PendingModifiedValues": {},
            "TagList": []
        }
    }

For more information, see `Deleting an RDS for Oracle tenant database from your CDB <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/oracle-cdb-configuring.deleting.pdb.html>`__ in the *Amazon RDS User Guide*.
