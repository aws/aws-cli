**To publish a batch of messages to an SNS topic**

The following ``publish-batch`` example publishes two messages to the specified SNS topic in a single request. ::

    aws sns publish-batch \
        --topic-arn arn:aws:sns:us-west-2:123456789012:my-topic \
        --publish-batch-request-entries Id=msg1,Message=hello Id=msg2,Message=world

Output::

    {
        "Successful": [
            {
                "Id": "msg1",
                "MessageId": "123a45b6-7890-12c3-45d6-111122223333"
            },
            {
                "Id": "msg2",
                "MessageId": "123a45b6-7890-12c3-45d6-444455556666"
            }
        ],
        "Failed": []
    }
