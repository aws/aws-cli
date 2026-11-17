**To retrieve the content and settings of a message template for messages that are sent through the SMS channel**

The following ``get-sms-template`` example retrieves the content and settings of a SMS message template. ::

    aws pinpoint get-sms-template \
        --template-name TestTemplate

Output::

    {
        "SMSTemplateResponse": {
            "Arn": "arn:aws:mobiletargeting:us-west-2:AIDACKCEVSQ6C2EXAMPLE:templates/TestTemplate/SMS",
            "Body": "hello\n how are you?\n food is good",
            "CreationDate": "2023-06-20T21:37:30.124Z",
            "LastModifiedDate": "2023-06-20T21:37:30.124Z",
            "tags": {},
            "TemplateDescription": "Test SMS Template",
            "TemplateName": "TestTemplate",
            "TemplateType": "SMS",
            "Version": "1"
        }
    }

For more information, see `Amazon Pinpoint message templates <https://docs.aws.amazon.com/pinpoint/latest/userguide/messages-templates.html>`__ in the *Amazon Pinpoint User Guide*.