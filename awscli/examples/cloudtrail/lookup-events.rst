**To look up events for a trail**

The following ``lookup-events`` example looks up API activity events by the attribute ``EventName``. ::

    aws cloudtrail lookup-events \
        --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin

Output::

    {
        "Events": [
            {
                "EventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Username": "my-session-name",
                "EventTime": "2021-11-18T09:41:02-08:00",
                "CloudTrailEvent": "{\"eventVersion\":\"1.02\",\"userIdentity\":{\"type\":\"AssumedRole\",\"principalId\":\"AROAJIKPFTA72SWU4L7T4:my-session-name\",\"arn\":\"arn:aws:sts::123456789012:assumed-role/my-role/my-session-name\",\"accountId\":\"123456789012\",\"sessionContext\":{\"attributes\":{\"mfaAuthenticated\":\"false\",\"creationDate\":\"2016-01-26T21:42:12Z\"},\"sessionIssuer\":{\"type\":\"Role\",\"principalId\":\"AROAJIKPFTA72SWU4L7T4\",\"arn\":\"arn:aws:iam::123456789012:role/my-role\",\"accountId\":\"123456789012\",\"userName\":\"my-role\"}}},\"eventTime\":\"2016-01-26T21:42:12Z\",\"eventSource\":\"signin.amazonaws.com\",\"eventName\":\"ConsoleLogin\",\"awsRegion\":\"us-west-2\",\"sourceIPAddress\":\"72.21.198.70\",\"userAgent\":\"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36\",\"requestParameters\":null,\"responseElements\":{\"ConsoleLogin\":\"Success\"},\"additionalEventData\":{\"MobileVersion\":\"No\",\"MFAUsed\":\"No\"},\"eventID\":\"a1b2c3d4-5678-90ab-cdef-EXAMPLE11111\",\"eventType\":\"AwsConsoleSignIn\",\"recipientAccountId\":\"123456789012\"}",
                "EventName": "ConsoleLogin",
                "Resources": []
            }
        ]
    }

For more information, see `Viewing recent management events with the AWS CLI <https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events-cli.html>`__ in the *AWS CloudTrail User Guide*.
