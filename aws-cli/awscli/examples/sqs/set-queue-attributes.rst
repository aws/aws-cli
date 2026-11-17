**To set queue attributes**

The following ``set-queue-attributes`` example sets the specified queue to a delivery delay of 10 seconds, a maximum message size of 128 KB (128 KB * 1,024 bytes), a message retention period of 3 days (3 days * 24 hours * 60 minutes * 60 seconds), a receive message wait time of 20 seconds, and a default visibility timeout of 60 seconds. This example also associates the specified dead letter queue with a maximum receive count of 1,000 messages. ::

    aws sqs set-queue-attributes \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyNewQueue \
        --attributes file://set-queue-attributes.json

Contents of ``set-queue-attributes.json``::

    {
        "DelaySeconds": "10",
        "MaximumMessageSize": "131072",
        "MessageRetentionPeriod": "259200",
        "ReceiveMessageWaitTimeSeconds": "20",
        "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-west-2:80398EXAMPLE:MyDeadLetterQueue\",\"maxReceiveCount\":\"1000\"}",
        "VisibilityTimeout": "60"
    }

This command produces no output.

For more information, see `Configuring queue parameters using the Amazon SQS console <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-configure-queue-parameters.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
