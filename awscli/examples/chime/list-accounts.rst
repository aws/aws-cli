**To get a list of accounts**

The following ``list-accounts`` example retrieves a list of the Amazon Chime accounts in the administrator's AWS account. ::

    aws chime list-accounts

Output::

    {
        "Accounts": [
            {
                "AwsAccountId": "123456789012",
                "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Name": "First Chime Account",
                "AccountType": "EnterpriseDirectory",
                "CreatedTimestamp": "2018-12-20T18:38:02.181Z",
                "DefaultLicense": "Pro",
                "SupportedLicenses": [
                    "Basic",
                    "Pro"
                ],
                "SigninDelegateGroups": [
                    {
                        "GroupName": "myGroup"
                    }
                ]
            },
            {
                "AwsAccountId": "123456789012",
                "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Name": "Second Chime Account",
                "AccountType": "Team",
                "CreatedTimestamp": "2018-09-04T21:44:22.292Z",
                "DefaultLicense": "Pro",
                "SupportedLicenses": [
                    "Basic",
                    "Pro"
                ],
                "SigninDelegateGroups": [
                    {
                        "GroupName": "myGroup"
                    }
                ]
            }
        ]
    }

For more information, see `Managing your Amazon Chime accounts <https://docs.aws.amazon.com/chime/latest/ag/manage-chime-account.html>`__ in the *Amazon Chime Administration Guide*.
