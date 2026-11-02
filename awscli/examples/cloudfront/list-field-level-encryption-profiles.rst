**To list CloudFront field-level encryption profiles**

The following ``list-field-level-encryption-profiles`` example gets a list of the CloudFront field-level encryption
profiles in your AWS account. ::

    aws cloudfront list-field-level-encryption-profiles

Output::

    {
        "FieldLevelEncryptionProfileList": {
            "MaxItems": 100,
            "Quantity": 2,
            "Items": [
                {
                    "Id": "P280MFCLSYOCVU",
                    "LastModifiedTime": "2019-12-05T01:05:39.896Z",
                    "Name": "ExampleFLEProfile",
                    "EncryptionEntities": {
                        "Quantity": 1,
                        "Items": [
                            {
                                "PublicKeyId": "K2K8NC4HVFE3M0",
                                "ProviderId": "ExampleFLEProvider",
                                "FieldPatterns": {
                                    "Quantity": 1,
                                    "Items": [
                                        "ExampleSensitiveField"
                                    ]
                                }
                            }
                        ]
                    },
                    "Comment": "FLE profile for AWS CLI example"
                },
                {
                    "Id": "PPK0UOSIF5WSV",
                    "LastModifiedTime": "2019-12-10T01:03:16.537Z",
                    "Name": "ExampleFLEProfile2",
                    "EncryptionEntities": {
                        "Quantity": 1,
                        "Items": [
                            {
                                "PublicKeyId": "K2ABC10EXAMPLE",
                                "ProviderId": "ExampleFLEProvider2",
                                "FieldPatterns": {
                                    "Quantity": 1,
                                    "Items": [
                                        "ExampleSensitiveField2"
                                    ]
                                }
                            }
                        ]
                    },
                    "Comment": "FLE profile #2 for AWS CLI example"
                }
            ]
        }
    }

For more information, see `Use field-level encryption to help protect sensitive data <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/field-level-encryption.html>`__ in the *Amazon CloudFront Developer Guide*.
