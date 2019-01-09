**To get account details**

This example retrieves details for the specified Amazon Chime account.

Command::

  aws chime get-account --account-id 12a3456b-7c89-012d-3456-78901e23fg45

Output::

{
    "Account": {
        "AwsAccountId": "111122223333",
        "AccountId": "12a3456b-7c89-012d-3456-78901e23fg45",
        "Name": "EnterpriseDirectory",
        "AccountType": "EnterpriseDirectory",
        "CreatedTimestamp": "2018-12-20T18:38:02.181Z",
        "DefaultLicense": "Pro",
        "SupportedLicenses": [
            "Basic",
            "Pro"
        ]
    }
}