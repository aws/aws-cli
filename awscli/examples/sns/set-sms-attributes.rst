**To set SMS message attributes**

The following ``set-sms-attributes`` example sets the default sender ID for SMS messages to ``MyName``. ::

    aws sns set-sms-attributes \
        --attributes DefaultSenderID=MyName

This command produces no output.

For more information, see `Setting SMS messaging preferences in Amazon SNS <https://docs.aws.amazon.com/sns/latest/dg/sms_preferences.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
