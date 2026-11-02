**To get identity pool roles**

The following ``get-identity-pool-roles`` example gets the roles for the specified identity pool. ::

    aws cognito-identity get-identity-pool-roles \
        --identity-pool-id "us-west-2:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "IdentityPoolId": "us-west-2:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Roles": {
            "authenticated": "arn:aws:iam::123456789012:role/Cognito_MyIdentityPoolAuth_Role",
            "unauthenticated": "arn:aws:iam::123456789012:role/Cognito_MyIdentityPoolUnauth_Role"
        }
    }

For more information, see `IAM roles <https://docs.aws.amazon.com/cognito/latest/developerguide/iam-roles.html>`__ in the *Amazon Cognito Developer Guide*.
