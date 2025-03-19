**To test a log transformer**

The following ``test-transformer`` example is used to test a log transformer. ::

    aws logs test-transformer \
        --transformer-config "[{\"grok\":{\"source\":\"@message\",\"match\":\"%{NUMBER:version} %{HOSTNAME:hostname} %{NOTSPACE:status} %{QUOTEDSTRING:logMsg}\"}},{\"addKeys\":{\"entries\":[{\"key\":\"environment\",\"value\":\"Prd-Application-01\",\"overwriteIfExists\":false}]}}]"
        --log-event-messages "293750 server-01.internal-network.local OK \"[Thread-000] token generated\""

Output::

{
    "transformedLogs": [
        {
            "eventNumber": 1,
            "eventMessage": "293750 server-01.internal-network.local OK \"[Thread-000] token generated\"",
            "transformedEventMessage": "{\"version\":\"293750\",\"hostname\":\"server-01.internal-network.local\",\"status\":\"OK\",\"logMsg\":\"[Thread-000] token generated\",\"environment\":\"Prd-Application-01\"}"
        }
    ]
}

For more information, see `Amazon CloudWatch Logs <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html>`__ in the *Amazon CloudWatch User Guide*.