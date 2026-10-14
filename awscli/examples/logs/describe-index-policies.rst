**To return returns the field index policies**

The following ``describe-index-policies`` example returns the field index policies of one or more log groups. ::

    aws logs describe-index-policies \
        --log-group-identifiers arn:aws:logs:us-east-1:123456789012:log-group:CWLG

Output::

{
    "indexPolicies": [
        {
            "logGroupIdentifier": "arn:aws:logs:us-east-1:123456789012:log-group:CWLG",
            "lastUpdateTime": 1738040112829,
            "policyDocument": "{\"Fields\":[\"@ingestionTime\",\"@requestId\"]}",
            "source": "LOG_GROUP"
        }
    ]
}

For more information, see `Amazon CloudWatch Logs <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html>`__ in the *Amazon CloudWatch User Guide*.