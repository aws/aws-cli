**To set identity pool roles**

The following ``set-identity-pool-roles`` example sets an identity pool role. ::

    aws cognito-identity set-identity-pool-roles \
        --identity-pool-id "us-west-2:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --roles authenticated="arn:aws:iam::123456789012:role/Cognito_MyIdentityPoolAuth_Role"

This command produces no output.

For more information, see `IAM roles <https://docs.aws.amazon.com/cognito/latest/developerguide/iam-roles.html>`__ in the *Amazon Cognito Developer Guide*.
