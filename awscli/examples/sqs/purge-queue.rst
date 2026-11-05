**To purge a queue**

The following ``purge-queue`` example deletes all messages in the specified queue. ::

    aws sqs purge-queue \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyNewQueue

This command produces no output.

For more information, see `Purging messages from an queue using the Amazon SQS console <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-using-purge-queue.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
