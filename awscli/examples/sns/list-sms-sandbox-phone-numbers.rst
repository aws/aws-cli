**To list the calling Amazon Web Services account’s destination phone numbers in the SMS sandbox**

The following `list-sms-sandbox-phone-numbers` example lists the destination phone numbers in the SMS sandbox. ::

    aws sns list-sms-sandbox-phone-numbers

Output::

    {
        "PhoneNumbers": [
            {
                "PhoneNumber": "+1555550100",
                "Status": "Verified"
            }
        ]
    }
