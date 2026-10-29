**To get the details about an account**

The following ``describe-account`` example requests details about an account. ::

    aws organizations describe-account \
        --account-id 555555555555

Output::

    {
        "Account": {
            "Id": "555555555555",
            "Arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/555555555555",
            "Name": "Beta account",
            "Email": "anika@example.com",
            "JoinedMethod": "INVITED",
            "JoinedTimestamp": 1481756563.134,
            "Paths": [
                "o-exampleorgid/r-examplerootid111/555555555555/"
            ],
            "State": "ACTIVE",
            "Status": "ACTIVE"
        }
    }
