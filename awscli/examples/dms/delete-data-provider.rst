**To delete a data provider**

The following ``delete-data-provider`` example deletes a data provider identified by its ARN. ::

    aws dms delete-data-provider \
        --data-provider-identifier arn:aws:dms:us-east-1:123456789012:data-provider:EXAMPLEABCDEFGHIJKLMNOPQRS

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
