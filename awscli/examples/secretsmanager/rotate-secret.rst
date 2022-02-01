**Example 1: To configure and start automatic rotation for a secret**

The following ``rotate-secret`` example configures and starts automatic rotation for a secret. Secrets Manager rotates the secret once immediately and then automatically every 10 days. The output shows the ``VersionId`` of the new secret version created by rotation. ::

    aws secretsmanager rotate-secret \
        --secret-id MyTestDatabaseSecret \
        --rotation-lambda-arn arn:aws:lambda:us-west-2:1234566789012:function:SecretsManagerTestRotationLambda \
        --rotation-rules AutomaticallyAfterDays=10

Output::

    {
        "ARN": "aws:arn:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
        "Name": "MyTestDatabaseSecret",
        "VersionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `This is the topic title <https://link.to.the/topic/page>`__ in the *Secrets Manager User Guide*.

**Example 2: To rotate a secret immediately**

The following ``rotate-secret`` example starts an immediate rotation. The output shows the ``VersionId`` of the new secret version created by rotation. The secret must already have rotation configured. ::

    aws secretsmanager rotate-secret \
        --secret-id MyTestDatabaseSecret

Output::

    {
        "ARN": "aws:arn:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
        "Name": "MyTestDatabaseSecret",
        "VersionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Rotate secrets <https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html>`__ in the *Secrets Manager User Guide*.