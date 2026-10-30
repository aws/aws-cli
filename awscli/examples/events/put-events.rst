**To send a custom event to CloudWatch Events**

The following ``put-events`` example sends a custom event to CloudWatch Events. The event is contained within the ``putevents.json`` file. ::

    aws events put-events \
        --entries file://putevents.json

Contents of ``putevents.json``::

    [
        {
            "Source": "com.mycompany.myapp",
            "Detail": "{ \"key1\": \"value1\", \"key2\": \"value2\" }",
            "Resources": [
                "resource1",
                "resource2"
            ],
            "DetailType": "myDetailType"
        },
        {
            "Source": "com.mycompany.myapp",
            "Detail": "{ \"key1\": \"value3\", \"key2\": \"value4\" }",
            "Resources": [
                "resource1",
                "resource2"
            ],
            "DetailType": "myDetailType"
        }
    ]

Output::

    {
        "FailedEntryCount": 0,
        "Entries": [
            {
                "EventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "EventId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

For more information, see `Sending events with PutEvents in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-putevents.html>`__ in the *Amazon EventBridge User Guide*.
