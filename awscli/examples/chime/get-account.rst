**To retrieve the details for an account**

The following ``get-account`` example retrieves the details for the specified Amazon Chime account. ::

    aws chime get-account \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Account": {
            "AwsAccountId": "123456789012",
            "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "Name": "EnterpriseDirectory",
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
        }
    }

For more information, see `Managing your Amazon Chime accounts <https://docs.aws.amazon.com/chime/latest/ag/manage-chime-account.html>`__ in the *Amazon Chime Administration Guide*.
