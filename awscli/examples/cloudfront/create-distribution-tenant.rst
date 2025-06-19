**To create a CloudFront distribution tenant**

The following ``create-distribution-tenant`` example creates a CloudFront distribution tenant that specifies customizations to disable WAF, add geo-restrictions, and use another certificate. ::

    aws cloudfront create-distribution-tenant \
        --cli-input-json file://tenant.json

Contents of ``tenant.json``::

    {
        "DistributionId": "E1XNX8R2GOAABC",
        "Domains": [
            {
                "Domain": "example.com"
            }
        ],
        "Parameters": [
            {
                "Name": "testParam",
                "Value": "defaultValue"
            }
        ],
        "ConnectionGroupId": "cg_2whCJoXMYCjHcxaLGrkllvyABC",
        "Enabled": false,
        "Tags": {
            "Items": [
                {
                    "Key": "tag",
                    "Value": "tagValue"
                }
            ]
        },
        "Name": "new-tenant-customizations",
        "Customizations": {
            "GeoRestrictions": {
                "Locations": ["DE"],
                "RestrictionType": "whitelist"
            },
            "WebAcl": {
                "Action": "disable"
            },
            "Certificate": {
                "Arn": "arn:aws:acm:us-east-1:123456789012:certificate/ec53f564-ea5a-4e4a-a0a2-e3c989449abc"
            }
        }
    }

Output::

    {
        "ETag": "E23ZP02F085ABC",
        "DistributionTenant": {
            "Id": "dt_2yN5tYwVbPKr7m2IB69M1yp1AB",
            "DistributionId": "E1XNX8R2GOAABC",
            "Name": "new-tenant-customizations",
            "Arn": "arn:aws:cloudfront::123456789012:distribution-tenant/dt_2yN5tYwVbPKr7m2IB69M1yp1AB",
            "Domains": [
                {
                    "Domain": "example.com",
                    "Status": "active"
                }
            ],
            "Tags": {
                "Items": [
                    {
                        "Key": "tag",
                        "Value": "tagValue"
                    }
                ]
            },
            "Customizations": {
                "WebAcl": {
                    "Action": "disable"
                },
                "Certificate": {
                    "Arn": "arn:aws:acm:us-east-1:123456789012:certificate/ec53f564-ea5a-4e4a-a0a2-e3c989449abc"
                },
                "GeoRestrictions": {
                    "RestrictionType": "whitelist",
                    "Locations": [
                        "DE"
                    ]
                }
            },
            "Parameters": [
                {
                    "Name": "testParam",
                    "Value": "defaultValue"
                }
            ],
            "ConnectionGroupId": "cg_2whCJoXMYCjHcxaLGrkllvyABC",
            "CreatedTime": "2025-06-11T17:20:06.432000+00:00",
            "LastModifiedTime": "2025-06-11T17:20:06.432000+00:00",
            "Enabled": false,
            "Status": "InProgress"
        }
    }

For more information, see `Create a distribution <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/distribution-web-creating-console.html>`__ in the *Amazon CloudFront Developer Guide*.
