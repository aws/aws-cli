**To check SMS message opt-out for a phone number**

The following ``check-if-phone-number-is-opted-out`` example checks whether the specified phone number is opted out of receiving SMS messages from the current AWS account. ::

    aws sns check-if-phone-number-is-opted-out \
        --phone-number +1555550100

Output::

    {
        "isOptedOut": false
    }

For more information, see `Managing Amazon SNS phone numbers and subscriptions <https://docs.aws.amazon.com/sns/latest/dg/sms_manage.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
