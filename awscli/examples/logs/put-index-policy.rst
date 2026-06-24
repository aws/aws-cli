**To create or update a field index policy**

The following ``put-index-policy`` example creates or updates a field index policy for the specified log group. ::

	aws logs put-index-policy \
        --log-group-identifier arn:aws:logs:us-east-1:123456789012:log-group:CWLG \
        --policy-document "{\"Fields\":[\"@ingestionTime\",\"@requestId\"]}"

Output::

{
    "indexPolicy": {
        "logGroupIdentifier": "arn:aws:logs:us-east-1:123456789012:log-group:CWLG",
        "lastUpdateTime": 1738040112829,
        "policyDocument": "{\"Fields\":[\"@ingestionTime\",\"@requestId\"]}",
        "source": "LOG_GROUP"
    }
}

For more information, see `Amazon CloudWatch Logs <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html>`__ in the *Amazon CloudWatch User Guide*.