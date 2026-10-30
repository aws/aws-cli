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

The following ``list-queues`` example lists only queues that start with "My". ::

    aws sqs list-queues --queue-name-prefix My

Output::

    {
        "QueueUrls": [
            "https://queue.amazonaws.com/80398EXAMPLE/MyDeadLetterQueue",
            "https://queue.amazonaws.com/80398EXAMPLE/MyQueue",
            "https://queue.amazonaws.com/80398EXAMPLE/MyOtherQueue"
        ]
    }