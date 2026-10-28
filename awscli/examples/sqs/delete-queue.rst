**To delete a queue**

The following ``delete-queue`` example deletes the specified queue. This command produces no output. ::

    aws sqs delete-queue \
        --queue-url https://sqs.us-east-1.amazonaws.com/80398EXAMPLE/MyNewerQueue
