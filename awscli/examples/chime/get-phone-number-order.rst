**To get details for a phone number order**

The following ``get-phone-number-order`` example displays the details of the specified phone number order. ::

    aws chime get-phone-number-order \
        --phone-number-order-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "PhoneNumberOrder": {
            "PhoneNumberOrderId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "ProductType": "VoiceConnector",
            "Status": "Partial",
            "OrderedPhoneNumbers": [
                {
                    "E164PhoneNumber": "+12065550100",
                    "Status": "Acquired"
                },
                {
                    "E164PhoneNumber": "+12065550101",
                    "Status": "Acquired"
                },
                {
                    "E164PhoneNumber": "+12065550102",
                    "Status": "Failed"
                }
            ],
            "CreatedTimestamp": "2019-08-09T21:35:21.427Z",
            "UpdatedTimestamp": "2019-08-09T21:35:31.926Z"
        }
    }

For more information, see `Working with Phone Numbers <https://docs.aws.amazon.com/chime/latest/ag/phone-numbers.html>`__ in the *Amazon Chime Administration Guide*.
