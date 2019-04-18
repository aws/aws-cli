**To describe an activation**

This example provides details about the activations on your account.

Command::

  aws ssm describe-activations

Output::

  {
    "ActivationList": [
        {
            "ActivationId": "bcf6faa8-83fd-419e-9534-96ad14131eb7",
            "Description": "test",
            "DefaultInstanceName": "MyWebServers",
            "IamRole": "AutomationRole",
            "RegistrationLimit": 10,
            "RegistrationsCount": 0
            "ExpirationDate": 1550176478.734,
            "Expired": false,
            "CreatedDate": 1550090078.734
        }
    ]
  }
