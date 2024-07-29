**To create a subscriber with data access**

The following ``create-subscriber`` example creates a subscriber in Security Lake with access to data in the current AWS Region for the specified subscriber identity for an AWS source. ::

    aws securitylake create-subscriber \
        --access-types "S3" \
        --sources '[{"awsLogSource": {"sourceName": "VPC_FLOW","sourceVersion": "2.0"}}]' \
        --subscriber-name "opensearch-s3" \
        --subscriber-identity '{"principal": "029189416600","externalId": "123456789012"}'

Output::

    {
        "subscriber": {
            "accessTypes": [
                "S3"
            ],
            "createdAt": "2024-07-17T19:08:26.787000+00:00",
            "roleArn": "arn:aws:iam::773172568199:role/AmazonSecurityLake-896f218b-cfba-40be-a255-8b49a65d0407",
            "s3BucketArn": "arn:aws:s3:::aws-security-data-lake-us-east-1-um632ufwpvxkyz0bc5hkb64atycnf3",
            "sources": [
                {
                    "awsLogSource": {
                        "sourceName": "VPC_FLOW",
                        "sourceVersion": "2.0"
                    }
                }
            ],
            "subscriberArn": "arn:aws:securitylake:us-east-1:773172568199:subscriber/896f218b-cfba-40be-a255-8b49a65d0407",
            "subscriberId": "896f218b-cfba-40be-a255-8b49a65d0407",
            "subscriberIdentity": {
                "externalId": "123456789012",
                "principal": "029189416600"
            },
            "subscriberName": "opensearch-s3",
            "subscriberStatus": "ACTIVE",
            "updatedAt": "2024-07-17T19:08:27.133000+00:00"
        }
    }

For more information, see `Creating a subscriber with data access <https://docs.aws.amazon.com/security-lake/latest/userguide/subscriber-data-access.html#create-subscriber-data-access>`__ in the *Amazon Security Lake User Guide*.