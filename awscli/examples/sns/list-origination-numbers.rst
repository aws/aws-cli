**To list the calling Amazon Web Services account’s dedicated origination numbers and their metadata**

The following `list-origination-numbers` example lists the dedicated phone numbers associated with your Amazon Web Services account. ::

    aws sns list-origination-numbers

Output::

    {
        "PhoneNumbers": [
            {
                "CreatedAt": "2024-10-01T12:34:56.789Z",
                "PhoneNumber": "+1555550100",
                "Status": "ACTIVE",
                "Iso2CountryCode": "US",
                "RouteType": "Transactional",
                "NumberCapabilities": [
                    "SMS"
                ]
            }
        ]
    }
