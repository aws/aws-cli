**To get a queue URL**

The following ``get-queue-url`` example gets the specified queue's URL. ::

    aws sqs get-queue-url --queue-name MyQueue

Output::

    {
        "QueueUrl": "https://queue.amazonaws.com/80398EXAMPLE/MyQueue"
    }