**To create an account**

The following ``create-account`` example creates an Amazon Chime account under the administrator's AWS account. ::

    aws chime create-account \
        --name MyChimeAccount

Output::

    {
        "Account": {
            "AwsAccountId": "123456789012",
            "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "Name": "MyChimeAccount",
            "AccountType": "Team",
            "CreatedTimestamp": "2019-01-04T17:11:22.003Z",
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

For more information, see `Getting started <https://docs.aws.amazon.com/chime/latest/ag/getting-started.html>`__ in the *Amazon Chime Administration Guide*.
