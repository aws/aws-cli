**To delete multiple messages as a batch**

The following ``delete-message-batch`` example deletes the specified messages. ::

    aws sqs delete-message-batch \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyQueue \
        --entries file://delete-message-batch.json

Contents of ``delete-message-batch.json``::

    [
        {
            "Id": "FirstMessage",
            "ReceiptHandle": "AQEB1mgl...Z4GuLw=="
        },
        {
            "Id": "SecondMessage",
            "ReceiptHandle": "AQEBLsYM...VQubAA=="
        }
    ]

Output::

    {
        "Successful": [
            {
                "Id": "FirstMessage"
            },
            {
                "Id": "SecondMessage"
            }
        ]
    }

For more information, see `Amazon SQS batch actions <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-batch-api-actions.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
