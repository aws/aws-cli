**To publish up to 10 messages to the specified topic in a single batch**

The following `publish-batch` example publishes multiple messages in a single batch. ::

    aws sns publish-batch \
        --topic-arn arn:aws:sns:us-east-1:123456789012:MyTopic.fifo \
        --publish-batch-request-entries '[{"Id": "10001", "Message": "message1"},{"Id": "10002", "Message": "message2"}]'

Output::

    {
        "Successful": [
            {
                "Id": "10001",
                "MessageId": "123a45b6-7890-12c3-45d6-333322221111",
                "SequenceNumber": "10000000000000009000"
            },
            {
                "Id": "10002",
                "MessageId": "ad0a5333-f45c-5d09-8393-087f5d11e3cd",
                "SequenceNumber": "1000000000000010000"
            }
        ],
        "Failed": []
    }