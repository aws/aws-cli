**To describe a conversion configuration**

The following ``describe-conversion-configuration`` example retrieves the conversion configuration for a migration project. ::

    aws dms describe-conversion-configuration \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS

Output::

    {
        "MigrationProjectIdentifier": "arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS",
        "ConversionConfiguration": "{\"Common project settings\":{\"ShowSeverityLevelInSql\":\"CRITICAL\",\"EnableGenAiConversion\":false},\"MSSQL_TO_AURORA_POSTGRESQL\":{\"ConvertProceduresToFunction\":true,\"UniqueIndexGeneration\":true,\"CaseSensitivityNames\":false},\"Conversion version\":{\"MSSQL_TO_AURORA_POSTGRESQL_target_engine_version\":\"15\"}}"
    }

For more information, see `Specifying schema conversion settings <https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion-settings.html>`__ in the *AWS Database Migration Service User Guide*.
