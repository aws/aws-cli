**To delete a message**

The following ``delete-message`` example deletes the specified message. ::

    aws sqs delete-message \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyQueue \
        --receipt-handle AQEBRXTo...q2doVA==

This command produces no output.

For more information, see `Receiving and deleting a message in Amazon SQS <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/step-receive-delete-message.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
