**To retrieve user settings**

The following ``get-user-settings`` example displays the specified user settings. ::

    aws chime get-user-settings \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --user-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "UserSettings": {
            "Telephony": {
                "InboundCalling": true,
                "OutboundCalling": true,
                "SMS": true
            }
        }
    }

For more information, see `Managing phone numbers in Amazon Chime <https://docs.aws.amazon.com/chime/latest/ag/phone-numbers.html>`__ in the *Amazon Chime Administration Guide*.
