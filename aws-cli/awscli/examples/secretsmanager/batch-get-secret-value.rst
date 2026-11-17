**Example 1: To retrieve the secret value for a group of secrets listed by name**

The following ``batch-get-secret-value`` example gets the secret value secrets for three secrets. ::

    aws secretsmanager batch-get-secret-value \
        --secret-id-list MySecret1 MySecret2 MySecret3

Output::


    {
        "SecretValues": [
            {
                "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MySecret1-a1b2c3",
                "Name": "MySecret1",
                "VersionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "SecretString": "{\"username\":\"diego_ramirez\",\"password\":\"EXAMPLE-PASSWORD\",\"engine\":\"mysql\",\"host\":\"secretsmanagertutorial.cluster.us-west-2.rds.amazonaws.com\",\"port\":3306,\"dbClusterIdentifier\":\"secretsmanagertutorial\"}",
                "VersionStages": [
                    "AWSCURRENT"
                ],
                "CreatedDate": "1523477145.729"
            },
            {
                "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MySecret2-a1b2c3",
                "Name": "MySecret2",
                "VersionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "SecretString": "{\"username\":\"akua_mansa\",\"password\":\"EXAMPLE-PASSWORD\"",
                "VersionStages": [
                    "AWSCURRENT"
                ],
                "CreatedDate": "1673477781.275"
            },
            {
                "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MySecret3-a1b2c3",
                "Name": "MySecret3",
                "VersionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "SecretString": "{\"username\":\"jie_liu\",\"password\":\"EXAMPLE-PASSWORD\"",
                "VersionStages": [
                    "AWSCURRENT"
                ],
                "CreatedDate": "1373477721.124"
            }
        ],
        "Errors": []
    }

For more information, see `Get a secret value using the AWS CLI <https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets_cli.html>`__ in the *AWS Secrets Manager User Guide*.

**Example 2: To retrieve the secret value for a group of secrets selected by filter**

The following ``batch-get-secret-value`` example gets the secret value secrets in your account that have ``MySecret`` in the name. Filtering by name is case sensitive. ::

    aws secretsmanager batch-get-secret-value \
        --filters Key="name",Values="MySecret"

Output::

    {
        "SecretValues": [
            {
                "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MySecret1-a1b2c3",
                "Name": "MySecret1",
                "VersionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "SecretString": "{\"username\":\"diego_ramirez\",\"password\":\"EXAMPLE-PASSWORD\",\"engine\":\"mysql\",\"host\":\"secretsmanagertutorial.cluster.us-west-2.rds.amazonaws.com\",\"port\":3306,\"dbClusterIdentifier\":\"secretsmanagertutorial\"}",
                "VersionStages": [
                    "AWSCURRENT"
                ],
                "CreatedDate": "1523477145.729"
            },
            {
                "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MySecret2-a1b2c3",
                "Name": "MySecret2",
                "VersionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "SecretString": "{\"username\":\"akua_mansa\",\"password\":\"EXAMPLE-PASSWORD\"",
                "VersionStages": [
                    "AWSCURRENT"
                ],
                "CreatedDate": "1673477781.275"
            },
            {
                "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MySecret3-a1b2c3",
                "Name": "MySecret3",
                "VersionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "SecretString": "{\"username\":\"jie_liu\",\"password\":\"EXAMPLE-PASSWORD\"",
                "VersionStages": [
                    "AWSCURRENT"
                ],
                "CreatedDate": "1373477721.124"
            }
        ],
        "Errors": []
    }

For more information, see `Get a secret value using the AWS CLI <https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets_cli.html>`__ in the *AWS Secrets Manager User Guide*.