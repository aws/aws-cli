**To add a permission to a queue**

The following ``add-permission`` example enables the specified AWS account to send messages to the specified queue. This command produces no output. ::

    aws sqs add-permission \
        --queue-url https://sqs.us-east-1.amazonaws.com/80398EXAMPLE/MyQueue \
        --label SendMessagesFromMyQueue \
        --aws-account-ids 12345EXAMPLE \
        --actions SendMessage
