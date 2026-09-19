**To create a tenant database**

The following ``create-tenant-database`` example creates a tenant database in an RDS for Oracle CDB instance. ::

    aws rds create-tenant-database \
        --db-instance-identifier test-rds-oracle \
        --tenant-db-name tenant2 \
        --master-username tenantadmin \
        --master-user-password secret99

Output::

    {
        "TenantDatabase": {
            "TenantDatabaseCreateTime": "2026-09-12T16:12:32.429000+00:00",
            "DBInstanceIdentifier": "test-rds-oracle",
            "TenantDBName": "TENANT2",
            "Status": "creating",
            "MasterUsername": "tenantadmin",
            "DbiResourceId": "db-ABCD1234EFGH5678IJKEXAMPLE",
            "TenantDatabaseResourceId": "tdb-ABCD1234EFGH5678IJKL90MNOPQRST1234UVWX5678YZAEXAMPLE",
            "TenantDatabaseARN": "arn:aws:rds:us-east-1:123456789012:tenant-database:tdb-abcd1234efgh5678ijkl90mnopqrst1234uvwx5678yzaexample",
            "CharacterSetName": "AL32UTF8",
            "NcharCharacterSetName": "AL16UTF16",
            "DeletionProtection": true,
            "PendingModifiedValues": {
                "MasterUserPassword": "****"
            },
            "TagList": []
        }
    }

For more information, see `Adding an RDS for Oracle tenant database to your CDB instance <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/oracle-cdb-configuring.adding.pdb.html>`__ in the *Amazon RDS User Guide*.
