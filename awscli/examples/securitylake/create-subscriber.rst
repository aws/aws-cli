**Example 1: To create a subscriber with data access**

The following ``create-subscriber`` example creates a subscriber in Security Lake with access to data in the current AWS Region for the specified subscriber identity for an AWS source. ::

    aws securitylake create-subscriber \
        --access-types "S3" \
        --sources '[{"awsLogSource": {"sourceName": "VPC_FLOW","sourceVersion": "2.0"}}]' \
        --subscriber-name 'opensearch-s3' \
        --subscriber-identity '{"principal": "123456789111","externalId": "123456789012"}'

Output::

    {
        "subscriber": {
            "accessTypes": [
                "S3"
            ],
            "createdAt": "2024-07-17T19:08:26.787000+00:00",
            "roleArn": "arn:aws:iam::123456789012:role/AmazonSecurityLake-896f218b-cfba-40be-a255-8b49a65d0407",
            "s3BucketArn": "arn:aws:s3:::amzn-s3-demo-bucket",
            "sources": [
                {
                    "awsLogSource": {
                        "sourceName": "VPC_FLOW",
                        "sourceVersion": "2.0"
                    }
                }
            ],
            "subscriberArn": "arn:aws:securitylake:us-west-2:123456789012:subscriber/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "subscriberId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "subscriberIdentity": {
                "externalId": "123456789012",
                "principal": "123456789111"
            },
            "subscriberName": "opensearch-s3",
            "subscriberStatus": "ACTIVE",
            "updatedAt": "2024-07-17T19:08:27.133000+00:00"
        }
    }

For more information, see `Creating a subscriber with data access <https://docs.aws.amazon.com/security-lake/latest/userguide/create-subscriber-data-access.html>`__ in the *Amazon Security Lake User Guide*.

**Example 2: To create a subscriber with query access**

The following ``create-subscriber`` example creates a subscriber in Security Lake with query access in the current AWS Region for the specified subscriber identity. ::

    aws securitylake create-subscriber \
        --access-types "LAKEFORMATION" \
        --sources '[{"awsLogSource": {"sourceName": "VPC_FLOW","sourceVersion": "2.0"}}]' \
        --subscriber-name 'opensearch-s3' \
        --subscriber-identity '{"principal": "123456789111","externalId": "123456789012"}'

Output::

    {
        "subscriber": {
            "accessTypes": [
                "LAKEFORMATION"
            ],
            "createdAt": "2024-07-18T01:05:55.853000+00:00",
            "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "resourceShareName": "LakeFormation-V2-NAMENAMENA-123456789012",
            "sources": [
                {
                    "awsLogSource": {
                        "sourceName": "VPC_FLOW",
                        "sourceVersion": "2.0"
                    }
                }
            ],
            "subscriberArn": "arn:aws:securitylake:us-west-2:123456789012:subscriber/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "subscriberId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "subscriberIdentity": {
                "externalId": "123456789012",
                "principal": "123456789111"
            },
            "subscriberName": "opensearch-s3",
            "subscriberStatus": "ACTIVE",
            "updatedAt": "2024-07-18T01:05:58.393000+00:00"
        }
    }

For more information, see `Creating a subscriber with query access <https://docs.aws.amazon.com/security-lake/latest/userguide/create-query-subscriber-procedures.html>`__ in the *Amazon Security Lake User Guide*.