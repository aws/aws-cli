**To retrieve information about the specified finding**

The following ``get-finding-v2`` example etrieves information about the specified finding in your AWS account. ::

    aws accessanalyzer get-finding-v2 \
        --analyzer-arn arn:aws:access-analyzer:us-west-2:123456789012:analyzer/ConsoleAnalyzer-organization \
        --id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "findingDetails": [
            {
                "externalAccessDetails": {
                    "action": [
                        "sts:AssumeRoleWithWebIdentity"
                    ],
                    "condition": {
                        "cognito-identity.amazonaws.com:aud": "us-west-2:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
                    },
                    "isPublic": false,
                    "principal": {
                        "Federated": "cognito-identity.amazonaws.com"
                    }
                }
            }
        ],
        "resource": "arn:aws:iam::123456789012:role/Cognito_testpoolAuth_Role",
        "status": "ACTIVE",
        "error": null,
        "createdAt": "2021-02-26T21:17:50.905000+00:00",
        "resourceType": "AWS::IAM::Role",
        "findingType": "ExternalAccess",
        "resourceOwnerAccount": "123456789012",
        "analyzedAt": "2024-02-16T18:17:47.888000+00:00",
        "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "updatedAt": "2021-02-26T21:17:50.905000+00:00"
    }

For more information, see `Reviewing findings <https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-findings-view.html>`__ in the *AWS IAM User Guide*.