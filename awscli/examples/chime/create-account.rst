**To create an account**

This example creates a new Amazon Chime account under the administrator's AWS account.

Command::

  aws chime create-account --name example

Output::

  {
    "Account": {
        "AwsAccountId": "111122223333",
        "AccountId": "12a3456b-7c89-012d-3456-78901e23fg45",
        "Name": "example",
        "AccountType": "Team",
        "CreatedTimestamp": "2019-01-04T17:11:22.003Z",
        "DefaultLicense": "Pro",
        "SupportedLicenses": [
            "Basic",
            "Pro"
        ]
    }
  }