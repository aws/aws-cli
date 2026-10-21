**To create a migration project**

The following ``create-migration-project`` example creates a migration project. ::

    aws dms create-migration-project \
        --migration-project-name example-migration-project \
        --description "Example migration project for documentation" \
        --source-data-provider-descriptors DataProviderIdentifier=arn:aws:dms:us-east-1:123456789012:data-provider:EXAMPLEABCDEFGHIJKLMNOPQRS,SecretsManagerSecretId=arn:aws:secretsmanager:us-east-1:123456789012:secret:example-source-secret-A1B2C3,SecretsManagerAccessRoleArn=arn:aws:iam::123456789012:role/example-secrets-manager-role \
        --target-data-provider-descriptors DataProviderIdentifier=arn:aws:dms:us-east-1:123456789012:data-provider:EXAMPLEABCDEFGHIJKLMNOPQRS,SecretsManagerSecretId=arn:aws:secretsmanager:us-east-1:123456789012:secret:example-target-secret-A1B2C3,SecretsManagerAccessRoleArn=arn:aws:iam::123456789012:role/example-secrets-manager-role \
        --instance-profile-identifier arn:aws:dms:us-east-1:123456789012:instance-profile:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --transformation-rules '{"rules":[{"rule-type":"transformation","rule-id":"1","rule-name":"1","rule-target":"schema","rule-action":"rename","object-locator":{"schema-name":"ExampleSchema"},"value":"TargetSchema"}]}' \
        --schema-conversion-application-attributes S3BucketPath=s3://amzn-s3-demo-bucket,S3BucketRoleArn=arn:aws:iam::123456789012:role/example-s3-access-role

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

For more information, see `Working with migration projects <https://docs.aws.amazon.com/dms/latest/userguide/migration-projects-create.html>`__ in the *AWS Database Migration Service User Guide*.
