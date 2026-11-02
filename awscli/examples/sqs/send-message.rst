**To send a message**

The following ``send-message`` example sends a message with the specified message body, delay period, and message attributes, to the specified queue. ::

    aws sqs send-message \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyQueue \
        --message-body "Information about the largest city in Any Region." \
        --delay-seconds 10 \
        --message-attributes file://send-message.json

Contents of ``send-message.json``::

    {
        "City": {
            "DataType": "String",
            "StringValue": "Any City"
        },
        "Greeting": {
            "DataType": "Binary",
            "BinaryValue": "Hello, World!"
        },
        "Population": {
            "DataType": "Number",
            "StringValue": "1250800"
        }
    }

Output::

    {
        "MD5OfMessageBody": "51b0a325...39163aa0",
        "MD5OfMessageAttributes": "00484c68...59e48f06",
        "MessageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Sending a message with attributes using Amazon SQS <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-using-send-message-with-attributes.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
