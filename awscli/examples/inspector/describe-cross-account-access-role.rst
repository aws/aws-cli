**To describe the cross account access role**

The following ``describe-cross-account-access-role`` example describes the IAM role that enables Amazon Inspector to access your AWS account. ::

    aws inspector describe-cross-account-access-role

Output::

    {
        "registeredAt": 1458069182.826,
        "roleArn": "arn:aws:iam::123456789012:role/inspector",
        "valid": true
    }

