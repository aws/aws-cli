**To create a queue**

The following ``create-queue`` example creates a queue with the specified name, sets the message retention period to 3 days (3 days * 24 hours * 60 minutes * 60 seconds), and sets the queue's dead letter queue to the specified queue with a maximum receive count of 1,000 messages. ::

    aws sqs create-queue \
        --queue-name MyQueue \
        --attributes file://create-queue.json

Contents of ``create-queue.json``::

    {
        "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-west-2:80398EXAMPLE:MyDeadLetterQueue\",\"maxReceiveCount\":\"1000\"}",
        "MessageRetentionPeriod": "259200"
    }

Output::

    {
        "QueueUrl": "https://queue.amazonaws.com/80398EXAMPLE/MyQueue"
    }

For more information, see `Using dead-letter queues in Amazon SQS <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
