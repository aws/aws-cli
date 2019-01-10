**To get a list of accounts**

This example lists the Amazon Chime accounts under the administrator's AWS account.

Command::

  aws chime list-accounts

Output::

  {
    "Accounts": [
        {
            "AwsAccountId": "111122223333",
            "AccountId": "12a3456b-7c89-012d-3456-78901e23fg45",
            "Name": "Example1",
            "AccountType": "EnterpriseDirectory",
            "CreatedTimestamp": "2018-12-20T18:38:02.181Z",
            "DefaultLicense": "Pro",
            "SupportedLicenses": [
                "Basic",
                "Pro"
            ]
        },
        {
            "AwsAccountId": "111122223333",
            "AccountId": "22a3456b-7c89-012d-3456-78901e23fg45",
            "Name": "Example2",
            "AccountType": "Team",
            "CreatedTimestamp": "2018-09-04T21:44:22.292Z",
            "DefaultLicense": "Pro",
            "SupportedLicenses": [
                "Basic",
                "Pro"
            ]
        }
    ]
  }
