**To retrieve a list of all of the accounts in a specified parent root or OU**

The following ``list-accounts-for-parent`` example requests a list of the accounts in an OU. ::

    aws organizations list-accounts-for-parent \
        --parent-id ou-examplerootid111-exampleouid111

The output includes a list of account summary objects.

Output::

    {
        "Accounts": [
            {
                "Arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/333333333333",
                "JoinedMethod": "INVITED",
                "JoinedTimestamp": 1481835795.536,
                "Id": "333333333333",
                "Name": "Development Account",
                "Email": "juan@example.com",
                "Paths": [
                    "o-exampleorgid/r-examplerootid111/111111111111/"
                ],
                "State": "ACTIVE",
                "Status": "ACTIVE"
            },
            {
                "Arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/444444444444",
                "JoinedMethod": "INVITED",
                "JoinedTimestamp": 1481835812.143,
                "Id": "444444444444",
                "Name": "Test Account",
                "Email": "anika@example.com",
                "Paths": [
                    "o-exampleorgid/r-examplerootid111/111111111111/"
                ],
                "State": "ACTIVE",
                "Status": "ACTIVE"
            }
        ]
    }

For more information, see `Managing accounts in an organization with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts.html>`__ in the *AWS Organizations User Guide*.
