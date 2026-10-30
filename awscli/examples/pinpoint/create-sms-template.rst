**To create a message template for messages that are sent through the SMS channel**

The following ``create-sms-template`` example creates a SMS message template. ::

    aws pinpoint create-sms-template \
        --template-name TestTemplate \
        --sms-template-request file://myfile.json

Contents of ``myfile.json``::

    {
        "Body": "hello\n how are you?\n food is good",
        "TemplateDescription": "Test SMS Template"
    }

Output::

    {
        "CreateTemplateMessageBody": {
            "Arn": "arn:aws:mobiletargeting:us-west-2:AIDACKCEVSQ6C2EXAMPLE:templates/TestTemplate/SMS",
            "Message": "Created",
            "RequestID": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
        }
    }

For more information, see `Amazon Pinpoint message templates <https://docs.aws.amazon.com/pinpoint/latest/userguide/messages-templates.html>`__ in the *Amazon Pinpoint User Guide*.