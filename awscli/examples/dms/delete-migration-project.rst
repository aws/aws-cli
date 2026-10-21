**To delete a migration project**

The following ``delete-migration-project`` example deletes a migration project identified by its ARN. ::

    aws dms delete-migration-project \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS

Output::

    {
        "MigrationProject": {
            "MigrationProjectName": "example-migration-project",
            "MigrationProjectArn": "arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS",
            "MigrationProjectCreationTime": "2026-01-09T12:30:00.000000+00:00",
            "SourceDataProviderDescriptors": [
                {
                    "SecretsManagerSecretId": "arn:aws:secretsmanager:us-east-1:123456789012:secret:example-source-secret-A1B2C3",
                    "SecretsManagerAccessRoleArn": "arn:aws:iam::123456789012:role/example-secrets-manager-role",
                    "DataProviderName": "example-data-provider",
                    "DataProviderArn": "arn:aws:dms:us-east-1:123456789012:data-provider:EXAMPLEABCDEFGHIJKLMNOPQRS"
                }
            ],
            "TargetDataProviderDescriptors": [
                {
                    "SecretsManagerSecretId": "arn:aws:secretsmanager:us-east-1:123456789012:secret:example-target-secret-A1B2C3",
                    "SecretsManagerAccessRoleArn": "arn:aws:iam::123456789012:role/example-secrets-manager-role",
                    "DataProviderName": "example-data-provider",
                    "DataProviderArn": "arn:aws:dms:us-east-1:123456789012:data-provider:EXAMPLEABCDEFGHIJKLMNOPQRS"
                }
            ],
            "InstanceProfileArn": "arn:aws:dms:us-east-1:123456789012:instance-profile:EXAMPLEABCDEFGHIJKLMNOPQRS",
            "InstanceProfileName": "example-instance-profile",
            "TransformationRules": "{\"rules\":[{\"rule-type\":\"transformation\",\"rule-id\":\"1\",\"rule-name\":\"1\",\"rule-target\":\"schema\",\"rule-action\":\"rename\",\"object-locator\":{\"schema-name\":\"ExampleSchema\"},\"value\":\"TargetSchema\"}]}",
            "Description": "Example migration project for documentation",
            "SchemaConversionApplicationAttributes": {
                "S3BucketPath": "s3://amzn-s3-demo-bucket",
                "S3BucketRoleArn": "arn:aws:iam::123456789012:role/example-s3-access-role"
            }
        }
    }

For more information, see `Working with migration projects <https://docs.aws.amazon.com/dms/latest/userguide/migration-projects-manage.html>`__ in the *AWS Database Migration Service User Guide*.
