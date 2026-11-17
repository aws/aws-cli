**To list SMS message opt-outs**

The following ``list-phone-numbers-opted-out`` example lists the phone numbers opted out of receiving SMS messages. ::

    aws sns list-phone-numbers-opted-out

Output::

    {
        "phoneNumbers": [
            "+15555550100"
        ]
    }

For more information, see `Managing Amazon SNS phone numbers and subscriptions <https://docs.aws.amazon.com/sns/latest/dg/sms_manage.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
