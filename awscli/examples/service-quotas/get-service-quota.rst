**To view a specific quota for a specific service in your AWS account**

The following **get-service-quota** command retrieves the current quota value for the ``Stack count`` quota of ``cloudformation`` service. ::

    aws service-quotas get-service-quota --service-code cloudformation --quota-code L-0485CB21

Output::

    {
        "Quota": {
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
    }

