**To describe an activation**

This example provides details about the activations on your account.

Command::

  aws ssm describe-activations

Output::

  {
    "ActivationList": [
        {
            "IamRole": "AutomationRole",
            "RegistrationLimit": 10,
            "ActivationId": "bcf6faa8-83fd-419e-9534-96ad14131eb7",
            "ExpirationDate": 1487887903.045,
            "CreatedDate": 1487801503.045,
            "DefaultInstanceName": "MyWebServers",
            "Expired": false,
            "RegistrationsCount": 0
        }
    ]
  }
