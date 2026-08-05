**To modify a conversion configuration**

The following ``modify-conversion-configuration`` example enables generative AI assisted conversion and updates a conversion path setting for a migration project. ::

    aws dms modify-conversion-configuration \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --conversion-configuration '{"Common project settings":{"EnableGenAiConversion":true},"MSSQL_TO_AURORA_POSTGRESQL":{"ConvertProceduresToFunction":false}}'

Output::

    {
        "MigrationProjectIdentifier": "arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS"
    }

For more information, see `Specifying schema conversion settings <https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion-settings.html>`__ in the *AWS Database Migration Service User Guide*.
