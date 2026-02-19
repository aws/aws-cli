**To list origination numbers**

The following ``list-origination-numbers`` example lists origination numbers associated with your account. ::

    aws sns list-origination-numbers

Output::

    {
        "PhoneNumbers": [
            {
                "CreatedAt": "2022-12-09T18:13:01.0+0000",
                "PhoneNumber": "+12065550199",
                "Status": "ACTIVE",
                "TwoWayChannelArn": "arn:aws:sns:us-east-1:123456789012:my-topic"
            }
        ]
    }
