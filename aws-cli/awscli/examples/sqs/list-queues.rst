**To list queues**

The following ``list-queues`` example lists all queues. ::

    aws sqs list-queues

Output::

    {
        "QueueUrls": [
            "https://queue.amazonaws.com/80398EXAMPLE/MyDeadLetterQueue",
            "https://queue.amazonaws.com/80398EXAMPLE/MyQueue",
            "https://queue.amazonaws.com/80398EXAMPLE/MyOtherQueue",
            "https://queue.amazonaws.com/80398EXAMPLE/TestQueue1",
            "https://queue.amazonaws.com/80398EXAMPLE/TestQueue2"
        ]
    }

For more information, see `Amazon SQS list queue pagination <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/list-all-queues-pagination.html>`__ in the *Amazon Simple Queue Service Developer Guide*.

The following ``list-queues`` example lists only queues that start with "My". ::

    aws sqs list-queues \
        --queue-name-prefix My

Output::

    {
        "QueueUrls": [
            "https://queue.amazonaws.com/80398EXAMPLE/MyDeadLetterQueue",
            "https://queue.amazonaws.com/80398EXAMPLE/MyQueue",
            "https://queue.amazonaws.com/80398EXAMPLE/MyOtherQueue"
        ]
    }

For more information, see `Amazon SQS list queue pagination <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/list-all-queues-pagination.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
