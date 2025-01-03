**To Return a list of saved CloudWatch Logs Insights query definitions**

The following ``describe-query-definitions`` example returns a paginated list of your saved CloudWatch Logs Insights query definitions. ::

    aws logs describe-query-definitions

Output::

    {
        "queryDefinitions": [
            {
                "queryDefinitionId": "a1b2c3d4-5678-90ab-cdef-example11111",
                "name": "Test/q1",
                "queryString": "filter eventSource=\"ec2.amazonaws.com\"\n| stats count(*) as eventCount by eventName, awsRegion\n| sort eventCount desc",
                "lastModified": 1715502206620,
                "logGroupNames": [
                    "demo-log-group"
                ]
            },
            {
                "queryDefinitionId": "a1b2c3d4-5678-90ab-cdef-example22222",
                "name": "Test/q2",
                "queryString": "fields @timestamp, @message\n| sort @timestamp asc\n| limit 20",
                "lastModified": 1654327955303,
                "logGroupNames": [
                    "example-log-group"
                ]
            }
        ]
    }

For more information, see `Log anomaly detection <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html>`__ in the *Amazon CloudWatch Logs User Guide*.