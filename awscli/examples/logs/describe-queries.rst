**To Return a list of CloudWatch Logs Insights queries**

The following ``describe-queries`` example returns a list of CloudWatch Logs Insights queries that are scheduled, running, or have been run recently in this account. ::

    aws logs describe-queries

Output::

    {
        "queries": [
            {
                "queryId": "a1b2c3d4-5678-90ab-cdef-example11111",
                "queryString": "SOURCE \"aws-cloudtrail-logs\" START=-3600s END=0s |\nstats count(*) by eventSource, eventName, awsRegion",
                "status": "Complete",
                "createTime": 1715501541961,
                "logGroupName": "demo-log-group"
            },
            {
                "queryId": "a1b2c3d4-5678-90ab-cdef-example22222",
                "queryString": "SOURCE \"Test\" START=-2592000s END=0s |\nfields @timestamp, @message, @logStream, @log\n| sort @timestamp desc\n| limit 1000",
                "status": "Complete",
                "createTime": 1715501468030,
                "logGroupName": "example-log-group"
            }
        ]
    }

For more information, see `Log anomaly detection <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html>`__ in the *Amazon CloudWatch Logs User Guide*.