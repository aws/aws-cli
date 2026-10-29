**To describe the log streams in a log group**

The following ``describe-log-streams`` example shows all log streams starting with the prefix ``2015`` in the log group ``my-logs``. ::

    aws logs describe-log-streams \
        --log-group-name my-logs \
        --log-stream-name-prefix 2015

Output::

    {
        "logStreams": [
            {
                "creationTime": 1433189871774,
                "arn": "arn:aws:logs:us-west-2:0123456789012:log-group:my-logs:log-stream:20150531",
                "logStreamName": "20150531",
                "storedBytes": 0
            },
            {
                "creationTime": 1433189873898,
                "arn": "arn:aws:logs:us-west-2:0123456789012:log-group:my-logs:log-stream:20150601",
                "logStreamName": "20150601",
                "storedBytes": 0
            }
        ]
    }

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html>`__ in the *Amazon CloudWatch Logs User Guide*.
