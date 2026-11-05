**To list AWS Direct Connect partners and locations**

The following ``describe-locations`` example lists AWS Direct Connect partners and locations in the current region. ::

    aws directconnect describe-locations

Output::

    {
        "locations": [
            {
                "locationName": "NAP do Brasil, Barueri, Sao Paulo",
                "locationCode": "TNDB"
            },
            {
                "locationName": "Tivit - Site Transamerica (Sao Paulo)",
                "locationCode": "TIVIT"
            }
        ]
    }

For more information, see `Requesting cross connects at Direct Connect locations <https://docs.aws.amazon.com/directconnect/latest/UserGuide/Colocation.html>`__ in the *AWS Direct Connect User Guide*.
