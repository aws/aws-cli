**To Test the filter pattern of a metric filter**

The following ``test-metric-filter`` example tests the filter pattern ``ERROR`` against a sample of log event messages. ::

    aws logs test-metric-filter \
        --filter-pattern ERROR \
        --log-event-messages "[ERROR] 400 BAD REQUEST" "[ERROR] 400 BAD REQUEST" "[INFO] 200 OK"

Output::

    {
        "matches": [
            {
                "eventNumber": 1,
                "eventMessage": "[ERROR] 400 BAD REQUEST",
                "extractedValues": {}
            },
            {
                "eventNumber": 2,
                "eventMessage": "[ERROR] 400 BAD REQUEST",
                "extractedValues": {}
            }
        ]
    }

For more information, see `Creating metrics from log events using filters <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html>`__ in the *Amazon CloudWatch Logs User Guide*.