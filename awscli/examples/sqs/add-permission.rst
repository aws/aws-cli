**To add a permission to a queue**

The following ``add-permission`` example enables the specified AWS account to send messages to the specified queue. ::

    aws sqs add-permission \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyQueue \
        --label SendMessagesFromMyQueue \
        --aws-account-ids 12345EXAMPLE \
        --actions SendMessage

This command produces no output.

For more information, see `Overview of managing access in Amazon SQS <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-overview-of-managing-access.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
