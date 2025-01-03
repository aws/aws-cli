**To Return information about a log group data protection policy**

The following ``get-data-protection-policy`` example returns information about a log group data protection policy. ::

    aws logs get-data-protection-policy \
        --log-group-identifier "arn:aws:logs:us-east-1:123456789012:log-group:demo-log-group"

Output::

    {
        "logGroupIdentifier": "demo-log-group",
        "policyDocument": "{\"Name\":\"data-protection-policy\",\"Description\":\"\",\"Version\":\"2021-06-01\",\"Statement\":[{\"Sid\":\"audit-policy\",\"DataIdentifier\":[\"arn:aws:dataprotection::aws:data-identifier/BankAccountNumber-US\"],\"Operation\":{\"Audit\":{\"FindingsDestination\":{\"CloudWatchLogs\":{\"LogGroup\":\"testloggroup\"}}}}},{\"Sid\":\"redact-policy\",\"DataIdentifier\":[\"arn:aws:dataprotection::aws:data-identifier/BankAccountNumber-US\"],\"Operation\":{\"Deidentify\":{\"MaskConfig\":{}}}}]}",
        "lastUpdatedTime": 1715504021257
    }

For more information, see `Encrypt log data in CloudWatch Logs using AWS Key Management Service <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html>`__ in the *Amazon CloudWatch Logs User Guide*.