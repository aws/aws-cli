**To list phone numbers for an Amazon Chime account**

The following ``list-phone-numbers`` example lists the phone numbers associated with the administrator's Amazon Chime account. ::

    aws chime list-phone-numbers

This command produces no output.
Output::

    {
        "PhoneNumbers": [
            {
                "PhoneNumberId": "%2B12065550100",
                "E164PhoneNumber": "+12065550100",
                "Type": "Local",
                "ProductType": "VoiceConnector",
                "Status": "Unassigned",
                "Capabilities": {
                    "InboundCall": true,
                    "OutboundCall": true,
                    "InboundSMS": true,
                    "OutboundSMS": true,
                    "InboundMMS": true,
                    "OutboundMMS": true
                },
                "Associations": [],
                "CreatedTimestamp": "2019-08-09T21:35:21.445Z",
                "UpdatedTimestamp": "2019-08-09T21:35:31.745Z"
            }
            {
                "PhoneNumberId": "%2B12065550101",
                "E164PhoneNumber": "+12065550101",
                "Type": "Local",
                "ProductType": "VoiceConnector",
                "Status": "Unassigned",
                "Capabilities": {
                    "InboundCall": true,
                    "OutboundCall": true,
                    "InboundSMS": true,
                    "OutboundSMS": true,
                    "InboundMMS": true,
                    "OutboundMMS": true
                },
                "Associations": [],
                "CreatedTimestamp": "2019-08-09T21:35:21.445Z",
                "UpdatedTimestamp": "2019-08-09T21:35:31.745Z"
            }
        ]
    }

For more information, see `Working with Phone Numbers <https://docs.aws.amazon.com/chime/latest/ag/phone-numbers.html>`__ in the *Amazon Chime Administration Guide*.
