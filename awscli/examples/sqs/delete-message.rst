**To delete a message**

The following ``delete-message`` example deletes the specified message. This command produces no output. ::

    aws sqs delete-message \
        --queue-url https://sqs.us-east-1.amazonaws.com/80398EXAMPLE/MyQueue \
        --receipt-handle AQEBRXTo...q2doVA==
