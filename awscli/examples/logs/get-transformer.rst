**To return the information about the log transformer**

The following ``get-transformer`` example returns the information about the log transformer associated with this log group. ::

	aws logs get-transformer \
        --log-group-identifier arn:aws:logs:us-east-1:123456789012:log-group:CWLG

Output::

{
    "logGroupIdentifier": "CWLG",
    "creationTime": 1734944243820,
    "lastModifiedTime": 1738037681546,
    "transformerConfig": [
        {
            "parseJSON": {}
        },
        {
            "addKeys": {
                "entries": [
                    {
                        "key": "metadata.transformed_in",
                        "value": "CloudWatchLogs",
                        "overwriteIfExists": false
                    },
                    {
                        "key": "feature",
                        "value": "Transformation",
                        "overwriteIfExists": false
                    }
                ]
            }
        },
        {
            "trimString": {
                "withKeys": [
                    "status"
                ]
            }
        }
    ]
}

For more information, see `Amazon CloudWatch Logs <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html>`__ in the *Amazon CloudWatch User Guide*.