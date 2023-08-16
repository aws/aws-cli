**To get control details**

The following ``batch-get-security-controls`` example gets details for Config.1 and IAM.1 in the current AWS account and AWS Region. ::

    aws securityhub batch-get-security-controls \
        --security-control-ids '["Config.1", "IAM.1"]'

Output::

    {
        "SecurityControls": [
            {
                "SecurityControlId": "Config.1",
                "SecurityControlArn": "arn:aws:securityhub:us-east-2:068873283051:security-control/Config.1",
                "Title": "AWS Config should be enabled",
                "Description": "This AWS control checks whether the Config service is enabled in the account for the local region and is recording all resources.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/Config.1/remediation",
                "SeverityRating": "MEDIUM",
                "SecurityControlStatus": "ENABLED"
            },
            {
                "SecurityControlId": "IAM.1",
                "SecurityControlArn": "arn:aws:securityhub:us-east-2:068873283051:security-control/IAM.1",
                "Title": "IAM policies should not allow full \"*\" administrative privileges",
                "Description": "This AWS control checks whether the default version of AWS Identity and Access Management (IAM) policies (also known as customer managed policies) do not have administrator access with a statement that has \"Effect\": \"Allow\" with \"Action\": \"*\" over \"Resource\": \"*\". It only checks for the Customer Managed Policies that you created, but not inline and AWS Managed Policies.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/IAM.1/remediation",
                "SeverityRating": "HIGH",
                "SecurityControlStatus": "ENABLED"
            }
        ]
    }

For more information, see `Viewing details for a control <https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-standards-control-details.html>`__ in the *AWS Security Hub User Guide*.