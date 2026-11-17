**To describe activations**

The following ``describe-activations`` example lists details about the activations in your AWS account. ::

    aws ssm describe-activations
  
Output::

    {
        "ActivationList": [
            {
                "ActivationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Description": "Example1",
                "IamRole": "HybridWebServersRole",
                "RegistrationLimit": 5,
                "RegistrationsCount": 5,
                "ExpirationDate": 1584316800.0,
                "Expired": false,
                "CreatedDate": 1581954699.792
            },
            {
                "ActivationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Description": "Example2",
                "IamRole": "HybridDatabaseServersRole",
                "RegistrationLimit": 5,
                "RegistrationsCount": 5,
                "ExpirationDate": 1580515200.0,
                "Expired": true,
                "CreatedDate": 1578064132.002
            }
        ]
    }

For more information, see `Step 4: Create a Managed-Instance Activation for a Hybrid Environment <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-managed-instance-activation.html>`__ in the *AWS Systems Manager User Guide*.
