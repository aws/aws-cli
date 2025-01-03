**To List or filter the log events from the specified log stream**

The following ``filter-log-events`` example list all the log events from the log group named ``demo-log-group``. ::

    aws logs filter-log-events \
        --log-group-name demo-log-group \

Output::

    {
        "events": [
            {
                "logStreamName": "teststream",
                "timestamp": 1712567843827,
                "message": "Test MESSAGE1",
                "ingestionTime": 1712567844822,
                "eventId": "00091539120382912324200901570000096855579456010247667712"
            },
            {
                "logStreamName": "2024/05/09/[$LATEST]abc1024",
                "timestamp": 1712568068991,
                "message": "Test MESSAGE2",
                "ingestionTime": 1712568070017,
                "eventId": "00001544141707904000000130886135001961903807164184002560"
            }
        ]
    }

For more information, see `Encrypt log data in CloudWatch Logs using AWS Key Management Service <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html>`__ in the *Amazon CloudWatch Logs User Guide*.