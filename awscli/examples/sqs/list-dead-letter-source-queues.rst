**To list dead letter source queues**

The following ``list-dead-letter-source-queues`` example lists the queues that are associated with the specified dead letter source queue. ::

    aws sqs list-dead-letter-source-queues \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyDeadLetterQueue

Output::

    {
        "queueUrls": [
            "https://queue.amazonaws.com/80398EXAMPLE/MyQueue",
            "https://queue.amazonaws.com/80398EXAMPLE/MyOtherQueue"
        ]
    }

For more information, see `Using dead-letter queues in Amazon SQS <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
