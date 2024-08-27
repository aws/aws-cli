**To create a subscriber with query access**

The following ``create-subscriber`` example creates a subscriber in Security Lake with query access in the current AWS Region for the specified subscriber identity. ::

    aws securitylake create-subscriber \
        --access-types "LAKEFORMATION" \
        --sources '[{"awsLogSource": {"sourceName": "VPC_FLOW","sourceVersion": "2.0"}}]' \
        --subscriber-name "opensearch-s3" \
        --subscriber-identity '{"principal": "029189416600","externalId": "123456789012"}'

Output::

    {
        "subscriber": {
            "accessTypes": [
                "LAKEFORMATION"
            ],
            "createdAt": "2024-07-18T01:05:55.853000+00:00",
            "resourceShareArn": "arn:aws:ram:us-east-1:123456789012:resource-share/8c31da49-c224-4f1e-bb12-37ab756d6d8a",
            "resourceShareName": "LakeFormation-V2-NAMENAMENA-123456789012",
            "sources": [
                {
                    "awsLogSource": {
                        "sourceName": "VPC_FLOW",
                        "sourceVersion": "2.0"
                    }
                }
            ],
            "subscriberArn": "arn:aws:securitylake:us-east-1:123456789012:subscriber/e762aabb-ce3d-4585-beab-63474597845d",
            "subscriberId": "e762aabb-ce3d-4585-beab-63474597845d",
            "subscriberIdentity": {
                "externalId": "123456789012",
                "principal": "029189416600"
            },
            "subscriberName": "opensearch-s3",
            "subscriberStatus": "ACTIVE",
            "updatedAt": "2024-07-18T01:05:58.393000+00:00"
        }
    }

For more information, see `Creating a subscriber with query access <https://docs.aws.amazon.com/security-lake/latest/userguide/subscriber-query-access.html#create-query-subscriber-procedures>`__ in the *Amazon Security Lake User Guide*.