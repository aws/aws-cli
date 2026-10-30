**To get a queue's attributes**

The following ``get-queue-attributes`` example gets all of the specified queue's attributes. ::

    aws sqs get-queue-attributes \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyQueue \
        --attribute-names All

Output::

    {
        "Attributes": {
            "ApproximateNumberOfMessagesNotVisible": "0",
            "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-west-2:80398EXAMPLE:MyDeadLetterQueue\",\"maxReceiveCount\":1000}",
            "MessageRetentionPeriod": "345600",
            "ApproximateNumberOfMessagesDelayed": "0",
            "MaximumMessageSize": "262144",
            "CreatedTimestamp": "1442426968",
            "ApproximateNumberOfMessages": "0",
            "ReceiveMessageWaitTimeSeconds": "0",
            "DelaySeconds": "0",
            "VisibilityTimeout": "30",
            "LastModifiedTimestamp": "1442426968",
            "QueueArn": "arn:aws:sqs:us-west-2:80398EXAMPLE:MyNewQueue"
        }
    }

For more information, see `Configuring queue parameters using the Amazon SQS console <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-configure-queue-parameters.html>`__ in the *Amazon Simple Queue Service Developer Guide*.

The following ``get-queue-attributes`` example gets only the specified queue's maximum message size and visibility timeout attributes. ::

    aws sqs get-queue-attributes \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyNewQueue \
        --attribute-names MaximumMessageSize VisibilityTimeout

Output::

    {
        "Attributes": {
            "VisibilityTimeout": "30",
            "MaximumMessageSize": "262144"
        }
    }

For more information, see `Configuring queue parameters using the Amazon SQS console <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-configure-queue-parameters.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
