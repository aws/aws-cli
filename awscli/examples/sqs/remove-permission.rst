**To remove a permission**

The following ``remove-permission`` example removes the permission with the specified label from the specified queue. ::

    aws sqs remove-permission \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyQueue \
        --label SendMessagesFromMyQueue

This command produces no output.

For more information, see `Overview of managing access in Amazon SQS <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-overview-of-managing-access.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
