**To get the details about an account**

The following ``describe-account`` example requests details about an account. ::

    aws organizations describe-account \
        --account-id 123456789444

Output::

    {
        "Account": {
            "Id": "123456789444",
            "Arn": "arn:aws:organizations::123456789012:account/o-exampleorgid/123456789444",
            "Name": "Beta account",
            "Email": "anika@example.com",
            "JoinedMethod": "INVITED",
            "JoinedTimestamp": 1481756563.134,
            "Paths": [
                "o-exampleorgid/r-examplerootid111/123456789444/"
            ],
            "State": "ACTIVE",
            "Status": "ACTIVE"
        }
    }

For more information, see `View details of an account in AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_view_account.html>`__ in the *AWS Organizations User Guide*.
