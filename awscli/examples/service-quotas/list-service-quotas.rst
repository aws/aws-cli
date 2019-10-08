**To view all service quotas for the specified AWS service in your AWS account**

The following **list-service-quotas** command retrieves the current quota values for all quotas in the of ``cloudformation`` service. ::

    aws service-quotas list-service-quotas --service-code cloudformation

Output::

    {
        "Quotas": [
            {
                "ServiceCode": "cloudformation",
                "ServiceName": "AWS CloudFormation",
                "QuotaArn": "arn:aws:servicequotas:us-east-1:123456789012:cloudformation/L-87D14FB7",
                "QuotaCode": "L-87D14FB7",
                "QuotaName": "Output count in CloudFormation template",
                "Value": 60.0,
                "Unit": "None",
                "Adjustable": false,
                "GlobalQuota": false
            },
            {
                "ServiceCode": "cloudformation",
                "ServiceName": "AWS CloudFormation",
                "QuotaArn": "arn:aws:servicequotas:us-east-1:123456789012:cloudformation/L-0485CB21",
                "QuotaCode": "L-0485CB21",
                "QuotaName": "Stack count",
                "Value": 200.0,
                "Unit": "None",
                "Adjustable": true,
                "GlobalQuota": false
            }
        ]

    }

