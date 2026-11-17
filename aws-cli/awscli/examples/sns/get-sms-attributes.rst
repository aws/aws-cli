**To list the default SMS message attributes**

The following ``get-sms-attributes`` example lists the default attributes for sending SMS messages. ::

    aws sns get-sms-attributes

Output::

    {
        "attributes": {
            "DefaultSenderID": "MyName"
        }
    }

For more information, see `Setting SMS messaging preferences in Amazon SNS <https://docs.aws.amazon.com/sns/latest/dg/sms_preferences.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
