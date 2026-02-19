**To list SMS sandbox destination phone numbers**

The following ``list-sms-sandbox-phone-numbers`` example lists destination phone numbers in your SMS sandbox. ::

    aws sns list-sms-sandbox-phone-numbers

Output::

    {
        "PhoneNumbers": [
            {
                "PhoneNumber": "+12065550100",
                "Status": "Verified"
            }
        ]
    }
