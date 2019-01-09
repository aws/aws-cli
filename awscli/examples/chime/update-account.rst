**To update an account**

This example updates the specified account name.

Command::

  aws chime update-account --account-id 12a3456b-7c89-012d-3456-78901e23fg45 --name Example3

Output::

{
    "Account": {
        "AwsAccountId": "111122223333",
        "AccountId": "12a3456b-7c89-012d-3456-78901e23fg45",
        "Name": "Example3",
        "AccountType": "Team",
        "CreatedTimestamp": "2018-09-04T21:44:22.292Z",
        "DefaultLicense": "Pro",
        "SupportedLicenses": [
            "Basic",
            "Pro"
        ]
    }
}