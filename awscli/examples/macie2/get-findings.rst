**To retrieve Amazon Macie findings**

The following ``get-findings`` example retrieves the details of up to 3 findings. ::

    aws macie2 get-findings \
        --finding-ids "64ed80b084b5b7b985b12345" "64ed80b084b5b7b985b67890" \
        --sort-criteria attributeName=severity.score,orderBy=DESC

Output::

    {
        "findings": [
            {
                "accountId": "123456789012",
                "archived": false,
                "category": "POLICY",
                "classificationDetails": {
                    "detailedResultsLocation": "s3://amzn-s3-demo-bucket/sensitive-data/results.json",
                    "jobArn": "arn:aws:macie2:us-east-1:123456789012:classification-job/42a1c188d7f838f9f0c1234567890",
                    "result": {
                        "status": {
                            "code": "COMPLETE"
                        }
                    }
                },
                "count": 2,
                "createdAt": "2023-05-07T20:21:01.656000+00:00",
                "description": "The S3 bucket is publicly readable.",
                "id": "64ed80b084b5b7b985b12345",
                "partition": "aws",
                "region": "us-east-1",
                "resourcesAffected": {
                    "s3Bucket": {
                        "arn": "arn:aws:s3:::amzn-s3-demo-bucket",
                        "name": "amzn-s3-demo-bucket",
                        "owner": {
                            "displayName": "example-user",
                            "id": "111122223333"
                        },
                        "publicAccess": {
                            "effectivePermission": "PUBLIC",
                            "permissionConfiguration": {
                                "bucketLevelPermissions": {
                                    "accessControlList": {
                                        "allowsPublicReadAccess": true,
                                        "allowsPublicWriteAccess": false
                                    }
                                }
                            }
                        }
                    }
                },
                "severity": {
                    "description": "High",
                    "score": 7.4
                },
                "title": "Bucket policy allows public read access",
                "type": "Policy:IAMUser/S3BucketPublicReadAccess",
                "updatedAt": "2023-05-07T20:21:01.656000+00:00"
            }
        ]
    }

**To retrieve findings with specific criteria**

The following ``get-findings`` example retrieves findings that match specific criteria, such as findings with high severity. ::

    aws macie2 get-findings \
        --finding-ids "64ed80b084b5b7b985b12345" \
        --sort-criteria attributeName=createdAt,orderBy=ASC

Output::

    {
        "findings": [
            {
                "accountId": "123456789012",
                "archived": false,
                "category": "CLASSIFICATION",
                "severity": {
                    "description": "High",
                    "score": 8.1
                },
                "title": "Sensitive data was detected in an S3 object",
                "type": "SensitiveData:S3Object/Personal"
            }
        ]
    }
