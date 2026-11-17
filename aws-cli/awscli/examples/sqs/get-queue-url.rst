**To get a queue URL**

The following ``get-queue-url`` example gets the specified queue's URL. ::

    aws sqs get-queue-url \
        --queue-name MyQueue

Output::

    {
        "QueueUrl": "https://queue.amazonaws.com/80398EXAMPLE/MyQueue"
    }

For more information, see `Amazon SQS queue and message identifiers <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-queue-message-identifiers.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
