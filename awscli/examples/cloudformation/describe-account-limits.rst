**To get information about your account limits**

The following ``describe-account-limits`` example retrieves a list of regional limits for the current account. ::

    aws cloudformation describe-account-limits

Output::

    {
        "AccountLimits": [
            {
                "Name": "StackLimit",
                "Value": 200
            },
            {
                "Name": "StackOutputsLimit",
                "Value": 60
            },
            {
                "Name": "ConcurrentResourcesLimit",
                "Value": 2500
            }
        ]
    }

For more information, see `Understand CloudFormation quotas <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cloudformation-limits.html>`__ in the *AWS CloudFormation User Guide*.
