**To retrieve a list of all of the accounts in an organization**

The following ``list-accounts`` example requests a list of the accounts in an organization. ::

    aws organizations list-accounts

The output includes a list of account summary objects.

Output::

    {
        "Accounts": [
            {
                "Arn": "arn:aws:organizations::123456789012:account/o-exampleorgid/123456789012",
                "JoinedMethod": "INVITED",
                "JoinedTimestamp": 1481830215.45,
                "Id": "123456789012",
                "Name": "Master Account",
                "Email": "bill@example.com",
                "Paths": [
                    "o-exampleorgid/r-examplerootid111/123456789012/"
                ],
                "State": "ACTIVE",
                "Status": "ACTIVE"
            },
            {
                "Arn": "arn:aws:organizations::123456789012:account/o-exampleorgid/123456789111",
                "JoinedMethod": "INVITED",
                "JoinedTimestamp": 1481835741.044,
                "Id": "123456789111",
                "Name": "Production Account",
                "Email": "alice@example.com",
                "Paths": [
                    "o-exampleorgid/r-examplerootid111/123456789012/"
                ],
                "State": "ACTIVE",
                "Status": "ACTIVE"
            },
            {
                "Arn": "arn:aws:organizations::123456789012:account/o-exampleorgid/123456789222",
                "JoinedMethod": "INVITED",
                "JoinedTimestamp": 1481835795.536,
                "Id": "123456789222",
                "Name": "Development Account",
                "Email": "juan@example.com",
                "Paths": [
                    "o-exampleorgid/r-examplerootid111/123456789012/"
                ],
                "State": "ACTIVE",
                "Status": "ACTIVE"
            },
            {
                "Arn": "arn:aws:organizations::123456789012:account/o-exampleorgid/123456789333",
                "JoinedMethod": "INVITED",
                "JoinedTimestamp": 1481835812.143,
                "Id": "123456789333",
                "Name": "Test Account",
                "Email": "anika@example.com",
                "Paths": [
                    "o-exampleorgid/r-examplerootid111/123456789012/"
                ],
                "State": "ACTIVE",
                "Status": "ACTIVE"
            }
        ]
    }

For more information, see `Managing accounts in an organization with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts.html>`__ in the *AWS Organizations User Guide*.
