**Example 1: To create a Microsoft SQL Server data provider**

The following ``create-data-provider`` example creates a Microsoft SQL Server data provider. ::

    aws dms create-data-provider \
        --data-provider-name example-data-provider \
        --engine sqlserver \
        --description "Example data provider for documentation" \
        --settings MicrosoftSqlServerSettings={ServerName=example-source-server.us-east-1.rds.amazonaws.com,Port=1433,DatabaseName=ExampleDatabase,SslMode=verify-full,CertificateArn=arn:aws:dms:us-east-1:123456789012:cert:EXAMPLEABCDEFGHIJKLMNOPQRS}

Output::

    {
        "DataProvider": {
            "DataProviderName": "example-data-provider",
            "DataProviderArn": "arn:aws:dms:us-east-1:123456789012:data-provider:EXAMPLEABCDEFGHIJKLMNOPQRS",
            "DataProviderCreationTime": "2026-01-09T12:30:00.000000+00:00",
            "Description": "Example data provider for documentation",
            "Engine": "sqlserver",
            "Settings": {
                "MicrosoftSqlServerSettings": {
                    "ServerName": "example-source-server.us-east-1.rds.amazonaws.com",
                    "Port": 1433,
                    "DatabaseName": "ExampleDatabase",
                    "SslMode": "verify-full",
                    "CertificateArn": "arn:aws:dms:us-east-1:123456789012:cert:EXAMPLEABCDEFGHIJKLMNOPQRS"
                }
            }
        }
    }

For more information, see `Working with data providers <https://docs.aws.amazon.com/dms/latest/userguide/data-providers.html>`__ in the *AWS Database Migration Service User Guide*.

**Example 2: To create a virtual data provider**

The following ``create-data-provider`` example creates a virtual data provider, which doesn't require a connection to the database. ::

    aws dms create-data-provider \
        --data-provider-name example-virtual-data-provider \
        --engine aurora-postgresql \
        --description "Example data provider for documentation" \
        --virtual \
        --settings PostgreSqlSettings={ServerName=virtual,Port=5432,DatabaseName=virtual,SslMode=none}

Output::

    {
        "DataProvider": {
            "DataProviderName": "example-virtual-data-provider",
            "DataProviderArn": "arn:aws:dms:us-east-1:123456789012:data-provider:EXAMPLEABCDEFGHIJKLMNOPQRS",
            "DataProviderCreationTime": "2026-01-09T12:30:00.000000+00:00",
            "Description": "Example data provider for documentation",
            "Engine": "aurora-postgresql",
            "Virtual": true,
            "Settings": {
                "PostgreSqlSettings": {
                    "ServerName": "virtual",
                    "Port": 5432,
                    "DatabaseName": "virtual",
                    "SslMode": "none"
                }
            }
        }
    }

For more information, see `Working with virtual data providers <https://docs.aws.amazon.com/dms/latest/userguide/virtual-data-provider.html>`__ in the *AWS Database Migration Service User Guide*.
