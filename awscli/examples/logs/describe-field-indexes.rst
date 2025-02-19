**To return a list of field indexes**

The following ``describe-field-indexes`` example returns a list of field indexes listed in the field index policies of one or more log groups. ::

	aws logs describe-field-indexes \
        --log-group-identifiers arn:aws:logs:us-east-1:123456789012:log-group:CWLG

Output:: 

{
    "fieldIndexes": [
        {
            "logGroupIdentifier": "arn:aws:logs:us-east-1:123456789012:log-group:CWLG",
            "fieldIndexName": "@logStream",
            "firstEventTime": 1738039122783,
            "lastEventTime": 1738039239900
        }
    ]
}

For more information, see `Amazon CloudWatch Logs <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html>`__ in the *Amazon CloudWatch User Guide*.