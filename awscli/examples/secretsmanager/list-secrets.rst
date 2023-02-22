**Example 1: To list the secrets in your account**

The following ``list-secrets`` example gets a list of the secrets in your account. ::

    aws secretsmanager list-secrets 

Output::

    {
        "SecretList": [
            {
                "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestSecret-a1b2c3",
                "Name": "MyTestSecret",
                "LastChangedDate": 1523477145.729,
                "SecretVersionsToStages": {
                    "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111": [
                        "AWSCURRENT"
                    ]
                }
            },
            {
                "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:AnotherSecret-d4e5f6",
                "Name": "AnotherSecret",
                "LastChangedDate": 1523482025.685,
                "SecretVersionsToStages": {
                    "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222": [
                        "AWSCURRENT"
                    ]
                }
            }
        ]
    }
    
For more information, see `Find a secret <https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_search-secret.html>`__ in the *Secrets Manager User Guide*.

**Example 2: To filter the list of secrets in your account**

The following ``list-secrets`` example gets a list of the secrets in your account that have ``Test`` in the name. Filtering by name is case sensitive. ::

    aws secretsmanager list-secrets \
        --filter Key="name",Values="Test" 

Output::

    {
        "SecretList": [
            {
                "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestSecret-a1b2c3",
                "Name": "MyTestSecret",
                "LastChangedDate": 1523477145.729,
                "SecretVersionsToStages": {
                    "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111": [
                        "AWSCURRENT"
                    ]
                }
            }
        ]
    }

For more information, see `Find a secret <https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_search-secret.html>`__ in the *Secrets Manager User Guide*.