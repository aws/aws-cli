**To change a message's timeout visibility**

The following ``change-message-visibility`` example changes the specified message's timeout visibility to 10 hours (10 hours * 60 minutes * 60 seconds). ::

    aws sqs change-message-visibility \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyQueue \
        --receipt-handle AQEBTpyI...t6HyQg== \
        --visibility-timeout 36000

This command produces no output.

For more information, see `Amazon SQS visibility timeout <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
