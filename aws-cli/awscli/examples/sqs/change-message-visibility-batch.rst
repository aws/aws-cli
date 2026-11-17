**To change multiple messages' timeout visibilities as a batch**

The following ``change-message-visibility-batch`` example changes the 2 specified messages' timeout visibilities to 10 hours (10 hours * 60 minutes * 60 seconds). ::

    aws sqs change-message-visibility-batch \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyQueue \
        --entries file://change-message-visibility-batch.json

Contents of ``change-message-visibility-batch.json``::

    [
        {
            "Id": "FirstMessage",
            "ReceiptHandle": "AQEBhz2q...Jf3kaw==",
            "VisibilityTimeout": 36000
        },
        {
            "Id": "SecondMessage",
            "ReceiptHandle": "AQEBkTUH...HifSnw==",
            "VisibilityTimeout": 36000
        }
    ]

Output::

    {
        "Successful": [
            {
                "Id": "SecondMessage"
            },
            {
                "Id": "FirstMessage"
            }
        ]
    }

For more information, see `Amazon SQS visibility timeout <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
