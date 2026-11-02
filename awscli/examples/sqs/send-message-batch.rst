**To send multiple messages as a batch**

The following ``send-message-batch`` example sends 2 messages with the specified message bodies, delay periods, and message attributes, to the specified queue. ::

    aws sqs send-message-batch \
        --queue-url https://sqs.us-west-2.amazonaws.com/80398EXAMPLE/MyQueue \
        --entries file://send-message-batch.json

Contents of ``send-message-batch.json``::

    [
        {
            "Id": "FuelReport-0001-2015-09-16T140731Z",
            "MessageBody": "Fuel report for account 0001 on 2015-09-16 at 02:07:31 PM.",
            "DelaySeconds": 10,
            "MessageAttributes": {
                "SellerName": {
                    "DataType": "String",
                    "StringValue": "Example Store"
                },
                "City": {
                    "DataType": "String",
                    "StringValue": "Any City"
                },
                "Region": {
                    "DataType": "String",
                    "StringValue": "WA"
                },
                "PostalCode": {
                    "DataType": "String",
                    "StringValue": "99065"
                },
                "PricePerGallon": {
                    "DataType": "Number",
                    "StringValue": "1.99"
                }
            }
        },
        {
            "Id": "FuelReport-0002-2015-09-16T140930Z",
            "MessageBody": "Fuel report for account 0002 on 2015-09-16 at 02:09:30 PM.",
            "DelaySeconds": 10,
            "MessageAttributes": {
                "SellerName": {
                    "DataType": "String",
                    "StringValue": "Example Fuels"
                },
                "City": {
                    "DataType": "String",
                    "StringValue": "North Town"
                },
                "Region": {
                    "DataType": "String",
                    "StringValue": "WA"
                },
                "PostalCode": {
                    "DataType": "String",
                    "StringValue": "99123"
                },
                "PricePerGallon": {
                    "DataType": "Number",
                    "StringValue": "1.87"
                }
            }
        }
    ]

Output::

    {
        "Successful": [
            {
                "MD5OfMessageBody": "203c4a38...7943237e",
                "MD5OfMessageAttributes": "10809b55...baf283ef",
                "Id": "FuelReport-0001-2015-09-16T140731Z",
                "MessageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "MD5OfMessageBody": "2cf0159a...c1980595",
                "MD5OfMessageAttributes": "55623928...ae354a25",
                "Id": "FuelReport-0002-2015-09-16T140930Z",
                "MessageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

For more information, see `Amazon SQS batch actions <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-batch-api-actions.html>`__ in the *Amazon Simple Queue Service Developer Guide*.
  
