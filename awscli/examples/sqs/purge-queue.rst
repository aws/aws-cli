**To purge a queue**

The following ``purge-queue`` example deletes all messages in the specified queue. This command produces no output. ::

    aws sqs purge-queue \
        --queue-url https://sqs.us-east-1.amazonaws.com/80398EXAMPLE/MyNewQueue
