**To remove a permission**

The following ``remove-permission`` example removes the permission with the specified label from the specified queue. This command produces no output. ::

    aws sqs remove-permission \
        --queue-url https://sqs.us-east-1.amazonaws.com/80398EXAMPLE/MyQueue \
        --label SendMessagesFromMyQueue
